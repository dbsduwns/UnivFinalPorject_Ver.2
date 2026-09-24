from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.models.user import User
from app.models.friendship import Friendship
from app.models.timetable import Timetable
from app.models.timetable_course import TimetableCourse
from app.models.course import Course
from app.models.custom_schedule import CustomSchedule

def check_is_friend(db: Session, user_a_id: int, user_b_id: int) -> bool:
    """두 사용자가 서로 ACCEPTED 상태의 친구인지 확인"""
    if user_a_id == user_b_id:
        return True
    return db.query(Friendship).filter(
        Friendship.status == "ACCEPTED",
        or_(
            and_(Friendship.requester_id == user_a_id, Friendship.addressee_id == user_b_id),
            and_(Friendship.requester_id == user_b_id, Friendship.addressee_id == user_a_id),
        )
    ).first() is not None

def search_users(db: Session, current_user: User, query: str) -> List[Dict[str, Any]]:
    query_str = query.strip()
    if not query_str:
        return []

    # 본인 제외, 학번 / 이름 / 이메일 검색
    users = (
        db.query(User)
        .filter(
            User.id != current_user.id,
            or_(
                User.student_id.ilike(f"%{query_str}%"),
                User.name.ilike(f"%{query_str}%"),
                User.email.ilike(f"%{query_str}%"),
            ),
        )
        .limit(20)
        .all()
    )

    results = []
    for target in users:
        # 관계 확인
        friendship = (
            db.query(Friendship)
            .filter(
                or_(
                    and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id),
                    and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id),
                )
            )
            .first()
        )

        status = "NONE"
        req_id = None
        if friendship:
            req_id = friendship.id
            if friendship.status == "ACCEPTED":
                status = "FRIEND"
            elif friendship.status == "PENDING":
                if friendship.requester_id == current_user.id:
                    status = "PENDING_SENT"
                else:
                    status = "PENDING_RECEIVED"
            elif friendship.status == "REJECTED":
                status = "NONE"  # 거절된 건 다시 신청 가능하도록 NONE

        results.append({
            "user": target,
            "friendship_status": status,
            "request_id": req_id
        })

    return results

def send_friend_request(
    db: Session,
    current_user: User,
    addressee_id: Optional[int] = None,
    student_id: Optional[str] = None
) -> Friendship:
    target_user = None
    if addressee_id:
        target_user = db.query(User).filter(User.id == addressee_id).first()
    elif student_id:
        target_user = db.query(User).filter(User.student_id == student_id.strip()).first()

    if not target_user:
        raise ValueError("사용자를 찾을 수 없습니다.")

    if target_user.id == current_user.id:
        raise ValueError("자기 자신에게는 친구 요청을 보낼 수 없습니다.")

    # 기존 관계 확인
    existing = (
        db.query(Friendship)
        .filter(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target_user.id),
                and_(Friendship.requester_id == target_user.id, Friendship.addressee_id == current_user.id),
            )
        )
        .first()
    )

    if existing:
        if existing.status == "ACCEPTED":
            raise ValueError("이미 친구 관계입니다.")
        if existing.status == "PENDING":
            if existing.requester_id == current_user.id:
                raise ValueError("이미 친구 요청을 보냈습니다.")
            else:
                # 상대방이 먼저 요청을 보낸 경우 즉시 수락 처리
                existing.status = "ACCEPTED"
                db.commit()
                db.refresh(existing)
                return existing
        elif existing.status == "REJECTED":
            # 거절된 이력이 있다면 다시 PENDING으로 갱신
            existing.requester_id = current_user.id
            existing.addressee_id = target_user.id
            existing.status = "PENDING"
            db.commit()
            db.refresh(existing)
            return existing

    new_request = Friendship(
        requester_id=current_user.id,
        addressee_id=target_user.id,
        status="PENDING",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

def get_friend_requests(db: Session, current_user: User) -> Dict[str, List[Dict[str, Any]]]:
    received_rows = (
        db.query(Friendship)
        .options(joinedload(Friendship.requester))
        .filter(
            Friendship.addressee_id == current_user.id,
            Friendship.status == "PENDING"
        )
        .order_by(Friendship.created_at.desc())
        .all()
    )

    sent_rows = (
        db.query(Friendship)
        .options(joinedload(Friendship.addressee))
        .filter(
            Friendship.requester_id == current_user.id,
            Friendship.status == "PENDING"
        )
        .order_by(Friendship.created_at.desc())
        .all()
    )

    return {
        "received": [
            {
                "id": r.id,
                "status": r.status,
                "created_at": r.created_at,
                "user": r.requester,
            }
            for r in received_rows
        ],
        "sent": [
            {
                "id": r.id,
                "status": r.status,
                "created_at": r.created_at,
                "user": r.addressee,
            }
            for r in sent_rows
        ],
    }

def accept_friend_request(db: Session, current_user: User, request_id: int) -> Friendship:
    request = (
        db.query(Friendship)
        .filter(Friendship.id == request_id, Friendship.addressee_id == current_user.id)
        .first()
    )
    if not request:
        raise ValueError("친구 요청을 찾을 수 없습니다.")

    if request.status == "ACCEPTED":
        return request

    request.status = "ACCEPTED"
    db.commit()
    db.refresh(request)
    return request

def reject_friend_request(db: Session, current_user: User, request_id: int) -> None:
    request = (
        db.query(Friendship)
        .filter(Friendship.id == request_id, Friendship.addressee_id == current_user.id)
        .first()
    )
    if not request:
        raise ValueError("친구 요청을 찾을 수 없습니다.")

    request.status = "REJECTED"
    db.commit()

def cancel_friend_request(db: Session, current_user: User, request_id: int) -> None:
    request = (
        db.query(Friendship)
        .filter(Friendship.id == request_id, Friendship.requester_id == current_user.id)
        .first()
    )
    if not request:
        raise ValueError("보낸 친구 요청을 찾을 수 없습니다.")

    db.delete(request)
    db.commit()

def get_friends(db: Session, current_user: User) -> List[User]:
    friendships = (
        db.query(Friendship)
        .options(joinedload(Friendship.requester), joinedload(Friendship.addressee))
        .filter(
            Friendship.status == "ACCEPTED",
            or_(
                Friendship.requester_id == current_user.id,
                Friendship.addressee_id == current_user.id,
            ),
        )
        .all()
    )

    friends = []
    for fs in friendships:
        if fs.requester_id == current_user.id:
            friends.append(fs.addressee)
        else:
            friends.append(fs.requester)

    friends.sort(key=lambda u: u.name)
    return friends

def delete_friend(db: Session, current_user: User, friend_id: int) -> None:
    friendship = (
        db.query(Friendship)
        .filter(
            Friendship.status == "ACCEPTED",
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == friend_id),
                and_(Friendship.requester_id == friend_id, Friendship.addressee_id == current_user.id),
            ),
        )
        .first()
    )
    if not friendship:
        raise ValueError("친구 관계가 존재하지 않습니다.")

    db.delete(friendship)
    db.commit()

def get_friend_timetables(db: Session, current_user: User, friend_id: int) -> List[Timetable]:
    if not check_is_friend(db, current_user.id, friend_id):
        raise PermissionError("친구가 아니면 시간표를 조회할 수 없습니다.")

    return (
        db.query(Timetable)
        .filter(Timetable.user_id == friend_id)
        .order_by(Timetable.is_main.desc(), Timetable.id.desc())
        .all()
    )

def get_friend_timetable_detail(
    db: Session,
    current_user: User,
    friend_id: int,
    timetable_id: Optional[int] = None
) -> Dict[str, Any]:
    if not check_is_friend(db, current_user.id, friend_id):
        raise PermissionError("친구가 아니면 시간표를 조회할 수 없습니다.")

    friend = db.query(User).filter(User.id == friend_id).first()
    if not friend:
        raise ValueError("해당 친구를 찾을 수 없습니다.")

    # 사용 가능한 모든 시간표 목록
    available_timetables = (
        db.query(Timetable)
        .filter(Timetable.user_id == friend_id)
        .order_by(Timetable.is_main.desc(), Timetable.id.desc())
        .all()
    )

    # 요청된 시간표가 없으면 메인 시간표, 없으면 첫 번째 시간표
    target_timetable = None
    if timetable_id:
        target_timetable = (
            db.query(Timetable)
            .filter(Timetable.id == timetable_id, Timetable.user_id == friend_id)
            .first()
        )
    else:
        target_timetable = (
            db.query(Timetable)
            .filter(Timetable.user_id == friend_id, Timetable.is_main == True)
            .first()
        )
        if not target_timetable and available_timetables:
            target_timetable = available_timetables[0]

    timetable_detail = None
    if target_timetable:
        timetable_courses = (
            db.query(TimetableCourse)
            .filter(TimetableCourse.timetable_id == target_timetable.id)
            .all()
        )
        course_ids = [item.course_id for item in timetable_courses]
        color_by_course_id = {item.course_id: item.color for item in timetable_courses}

        courses = []
        if course_ids:
            course_rows = (
                db.query(Course)
                .options(joinedload(Course.subject), joinedload(Course.schedules))
                .filter(Course.id.in_(course_ids))
                .all()
            )
            for course in course_rows:
                courses.append({
                    "id": course.id,
                    "subject_id": course.subject_id,
                    "subject_code": course.subject.subject_code if course.subject else None,
                    "name": course.subject.name if course.subject else None,
                    "credits": course.subject.credits if course.subject else None,
                    "section": course.section,
                    "professor": course.professor,
                    "color": color_by_course_id.get(course.id),
                    "schedules": course.schedules,
                })

        custom_schedules = (
            db.query(CustomSchedule)
            .filter(CustomSchedule.timetable_id == target_timetable.id)
            .all()
        )

        timetable_detail = {
            "id": target_timetable.id,
            "user_id": target_timetable.user_id,
            "name": target_timetable.name,
            "semester": target_timetable.semester,
            "is_main": target_timetable.is_main,
            "share_token": target_timetable.share_token,
            "created_at": target_timetable.created_at,
            "courses": courses,
            "custom_schedules": custom_schedules,
            "total_credits": sum(course.get("credits") or 0 for course in courses),
        }

    return {
        "friend": friend,
        "timetable": timetable_detail,
        "available_timetables": available_timetables,
    }

from sqlalchemy.orm import Session
from app.models.daily_menu import DailyMenu
from app.crawlers.menu_crawler import crawl_menu_list, save_menus

def get_daily_menu(db: Session, date: str):
    return db.query(DailyMenu).filter(DailyMenu.menu_date == date).all()

def crawl_and_save(max_items: int | None = None):
    menus = crawl_menu_list(max_items=max_items)
    save_menus(menus)
    return menus

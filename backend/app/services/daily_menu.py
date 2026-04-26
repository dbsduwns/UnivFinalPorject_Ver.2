from sqlalchemy.orm import Session
from app.models.daily_menu import DailyMenu
from app.crawlers.menu_crawler import crawl_menu_list, save_menus

def get_daily_menu(db: Session, date: str):
    return db.query(DailyMenu).filter(DailyMenu.menu_date == date).all()

def crawl_and_save():
    menus = crawl_menu_list
    save_menus(menus)
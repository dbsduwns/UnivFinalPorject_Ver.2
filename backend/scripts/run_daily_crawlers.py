from app.crawlers import menu_crawler, notice_crawler_v3, shuttle_crawler


def main():
    notice_crawler_v3.crawl_notices_safely(max_pages=5)

    menus = menu_crawler.crawl_menu_list()
    menu_crawler.save_menus(menus)

    schedule = shuttle_crawler.crawl_shuttle_schedule()
    shuttle_crawler.save_shuttle_schedule(schedule)


if __name__ == "__main__":
    main()
from app.crawlers import notice_crawler_v3, menu_crawler, shuttle_crawler

def main():
    notice_crawler_v3()
    menu_crawler()
    shuttle_crawler()

if __name__ == "__main__":
    main()
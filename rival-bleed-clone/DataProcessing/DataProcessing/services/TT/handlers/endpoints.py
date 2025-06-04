class TikTokAPIEndpoints:
    """
    API Endpoints for TikTok
    """

    #  (Tiktok Domain)
    TIKTOK_DOMAIN = "https://www.tiktok.com"

    #  (Webcast Domain)
    WEBCAST_DOMAIN = "https://webcast.tiktok.com"

    #  (Login)
    LOGIN_ENDPOINT = f"{TIKTOK_DOMAIN}/login/"

    #  (Home Recommend)
    HOME_RECOMMEND = f"{TIKTOK_DOMAIN}/api/recommend/item_list/"

    #  (User Detail Info)
    USER_DETAIL = f"{TIKTOK_DOMAIN}/api/user/detail/"

    #  (User Post)
    USER_POST = f"{TIKTOK_DOMAIN}/api/post/item_list/"

    #  (User Like)
    USER_LIKE = f"{TIKTOK_DOMAIN}/api/favorite/item_list/"

    #  (User Collect)
    USER_COLLECT = f"{TIKTOK_DOMAIN}/api/user/collect/item_list/"

    #  (User Play List)
    USER_PLAY_LIST = f"{TIKTOK_DOMAIN}/api/user/playlist/"

    #  (User Mix)
    USER_MIX = f"{TIKTOK_DOMAIN}/api/mix/item_list/"

    #  (Guess You Like)
    GUESS_YOU_LIKE = f"{TIKTOK_DOMAIN}/api/related/item_list/"

    #  (User Follow)
    USER_FOLLOW = f"{TIKTOK_DOMAIN}/api/user/list/"

    #  (User Fans)
    USER_FANS = f"{TIKTOK_DOMAIN}/api/user/list/"

    #  (Post Detail)
    POST_DETAIL = f"{TIKTOK_DOMAIN}/api/item/detail/"

    #  (Post Comment)
    POST_COMMENT = f"{TIKTOK_DOMAIN}/api/comment/list/"

    #  (Post Comment Reply)
    POST_COMMENT_REPLY = f"{TIKTOK_DOMAIN}/api/comment/list/reply/"

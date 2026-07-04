from bilibili_api import video_zone_v2


async def test_a_get_zone_list_sub_v2():
    return video_zone_v2.get_zone_list_sub_v2()


async def test_b_get_zone_info_by_tid_v2():
    return video_zone_v2.get_zone_info_by_tid_v2(tid_v2=1005)


async def test_c_get_zone_info_by_name_v2():
    return video_zone_v2.get_zone_info_by_name_v2("动画")


async def test_d_get_sub_zone_by_main_tid_v2():
    return video_zone_v2.get_sub_zone_by_main_tid_v2(tid_v2=1005)


async def test_e_get_zone_name_by_tid_v2():
    return video_zone_v2.get_zone_name_by_tid_v2(tid_v2=1005)


async def test_f_get_zone_url_by_tid_v2():
    return video_zone_v2.get_zone_url_by_tid_v2(tid_v2=1005)


async def test_g_get_tid_v2_by_zone_name():
    return video_zone_v2.get_tid_v2_by_zone_name(name="动画")


async def test_h_get_zone_v2_recommend():
    return await video_zone_v2.get_zone_v2_recommend(request_cnt=10, from_region=1003)

# Module video_zone_v2.py


bilibili_api.video_zone_v2

新版分区 (zone_v2) 相关操作，与频道不互通。


``` python
from bilibili_api import video_zone_v2
```

- [class VideoZoneTypesV2()](#class-VideoZoneTypesV2)
- [def get\_sub\_zone\_by\_main\_tid\_v2()](#def-get\_sub\_zone\_by\_main\_tid\_v2)
- [def get\_tid\_v2\_by\_zone\_name()](#def-get\_tid\_v2\_by\_zone\_name)
- [def get\_zone\_info\_by\_name\_v2()](#def-get\_zone\_info\_by\_name\_v2)
- [def get\_zone\_info\_by\_tid\_v2()](#def-get\_zone\_info\_by\_tid\_v2)
- [def get\_zone\_list\_sub\_v2()](#def-get\_zone\_list\_sub\_v2)
- [def get\_zone\_name\_by\_tid\_v2()](#def-get\_zone\_name\_by\_tid\_v2)
- [def get\_zone\_url\_by\_tid\_v2()](#def-get\_zone\_url\_by\_tid\_v2)
- [async def get\_zone\_v2\_recommend()](#async-def-get\_zone\_v2\_recommend)

---

## class VideoZoneTypesV2()

> Extend: `enum.Enum`

所有新版分区 (zone_v2) 枚举

- DOUGA: 动画
- DOUGA_FAN_ANIME: 同人动画
- DOUGA_GARAGE_KIT: 模玩周边
- DOUGA_COSPLAY: cosplay
- DOUGA_OFFLINE: 二次元线下
- DOUGA_EDITING: 动漫剪辑
- DOUGA_COMMENTARY: 动漫评论
- DOUGA_QUICK_VIEW: 动漫速读
- DOUGA_VOICE: 动漫配音
- DOUGA_INFORMATION: 动漫资讯
- DOUGA_INTERPRET: 网文解读
- DOUGA_VUP: 虚拟up主
- DOUGA_TOKUSATSU: 特摄
- DOUGA_PUPPETRY: 布袋戏
- DOUGA_COMIC: 漫画·动态漫
- DOUGA_MOTION: 广播剧
- DOUGA_REACTION: 动漫reaction
- DOUGA_TUTORIAL: 动漫教学
- DOUGA_OTHER: 二次元其他
- GAME: 游戏
- GAME_RPG: 单人RPG游戏
- GAME_MMORPG: MMORPG游戏
- GAME_STAND_ALONE: 单机主机类游戏
- GAME_SLG: SLG游戏
- GAME_TBS: 回合制策略游戏
- GAME_RTS: 即时策略游戏
- GAME_MOBA: MOBA游戏
- GAME_STG: 射击游戏
- GAME_SPG: 体育竞速游戏
- GAME_ACT: 动作竞技游戏
- GAME_MSC: 音游舞游
- GAME_SIM: 模拟经营游戏
- GAME_OTOME: 女性向游戏
- GAME_PUZ: 休闲/小游戏
- GAME_SANDBOX: 沙盒类
- GAME_OTHER: 其他游戏
- KICHIKU: 鬼畜
- KICHIKU_GUIDE: 鬼畜调教
- KICHIKU_THEATRE: 鬼畜剧场
- KICHIKU_MANUAL_VOCALOID: 人力VOCALOID
- KICHIKU_MAD: 音MAD
- KICHIKU_OTHER: 鬼畜综合
- MUSIC: 音乐
- MUSIC_ORIGINAL: 原创音乐
- MUSIC_MV: MV
- MUSIC_LIVE: 音乐现场
- MUSIC_FAN_VIDEOS: 乐迷饭拍
- MUSIC_COVER: 翻唱
- MUSIC_PERFORM: 演奏
- MUSIC_VOCALOID: VOCALOID
- MUSIC_AI_MUSIC: AI音乐
- MUSIC_RADIO: 电台·歌单
- MUSIC_TUTORIAL: 音乐教学
- MUSIC_COMMENTARY: 乐评盘点
- MUSIC_OTHER: 音乐综合
- DANCE: 舞蹈
- DANCE_OTAKU: 宅舞
- DANCE_HIPHOP: 街舞
- DANCE_GESTURES: 颜值·网红舞
- DANCE_STAR: 明星舞蹈
- DANCE_CHINA: 国风舞蹈
- DANCE_TUTORIAL: 舞蹈教学
- DANCE_BALLET: 芭蕾舞
- DANCE_WOTA: wota艺
- DANCE_OTHER: 舞蹈综合
- CINEPHILE: 影视
- CINEPHILE_COMMENTARY: 影视解读
- CINEPHILE_MONTAGE: 影视剪辑
- CINEPHILE_INFORMATION: 影视资讯
- CINEPHILE_PORTERAGE: 影视正片搬运
- CINEPHILE_SHORTFILM: 短剧短片
- CINEPHILE_AI: AI影视
- CINEPHILE_REACTION: 影视reaction
- CINEPHILE_OTHER: 影视综合
- ENT: 娱乐
- ENT_COMMENTARY: 娱乐评论
- ENT_MONTAGE: 明星剪辑
- ENT_FANS_VIDEO: 娱乐饭拍&现场
- ENT_INFORMATION: 娱乐资讯
- ENT_REACTION: 娱乐reaction
- ENT_VARIETY: 娱乐综艺正片
- ENT_OTHER: 娱乐综合
- KNOWLEDGE: 知识
- KNOWLEDGE_EXAM: 应试教育
- KNOWLEDGE_LANG_SKILL: 非应试语言学习
- KNOWLEDGE_CAMPUS: 大学专业知识
- KNOWLEDGE_BUSINESS: 商业财经
- KNOWLEDGE_SOCIAL_OBSERVATION: 社会观察
- KNOWLEDGE_POLITICS: 时政解读
- KNOWLEDGE_HUMANITY_HISTORY: 人文历史
- KNOWLEDGE_DESIGN: 设计艺术
- KNOWLEDGE_PSYCHOLOGY: 心理杂谈
- KNOWLEDGE_CAREER: 职场发展
- KNOWLEDGE_SCIENCE: 科学科普
- KNOWLEDGE_OTHER: 其他知识杂谈
- TECH: 科技数码
- TECH_COMPUTER: 电脑
- TECH_PHONE: 手机
- TECH_PAD: 平板电脑
- TECH_PHOTOGRAPHY: 摄影摄像
- TECH_MACHINE: 工程机械
- TECH_CREATE: 自制发明/设备
- TECH_OTHER: 科技数码综合
- INFORMATION: 资讯
- INFORMATION_POLITICS: 时政资讯
- INFORMATION_OVERSEAS: 海外资讯
- INFORMATION_SOCIAL: 社会资讯
- INFORMATION_OTHER: 综合资讯
- FOOD: 美食
- FOOD_MAKE: 美食制作
- FOOD_DETECTIVE: 美食探店
- FOOD_COMMENTARY: 美食测评
- FOOD_RECORD: 美食记录
- FOOD_OTHER: 美食综合
- SHORTPLAY: 小剧场
- SHORTPLAY_PLOT: 剧情演绎
- SHORTPLAY_LANG: 语言类小剧场
- SHORTPLAY_UP_VARIETY: UP主小综艺
- SHORTPLAY_INTERVIEW: 街头采访
- CAR: 汽车
- CAR_COMMENTARY: 汽车测评
- CAR_CULTURE: 汽车文化
- CAR_LIFE: 汽车生活
- CAR_TECH: 汽车技术
- CAR_OTHER: 汽车综合
- FASHION: 时尚美妆
- FASHION_MAKEUP: 美妆
- FASHION_SKINCARE: 护肤
- FASHION_COS: 仿装cos
- FASHION_OUTFITS: 鞋服穿搭
- FASHION_ACCESSORIES: 箱包配饰
- FASHION_JEWELRY: 珠宝首饰
- FASHION_TRICK: 三坑
- FASHION_COMMENTARY: 时尚解读
- FASHION_OTHER: 时尚综合
- SPORTS: 体育运动
- SPORTS_TREND: 潮流运动
- SPORTS_FOOTBALL: 足球
- SPORTS_BASKETBALL: 篮球
- SPORTS_RUNNING: 跑步
- SPORTS_KUNGFU: 武术
- SPORTS_FIGHTING: 格斗
- SPORTS_BADMINTON: 羽毛球
- SPORTS_INFORMATION: 体育资讯
- SPORTS_MATCH: 体育赛事
- SPORTS_OTHER: 体育综合
- ANIMAL: 动物
- ANIMAL_CAT: 猫
- ANIMAL_DOG: 狗
- ANIMAL_REPTILES: 小宠异宠
- ANIMAL_SCIENCE: 野生动物·动物解说科普
- ANIMAL_OTHER: 动物综合·二创
- VLOG: vlog
- VLOG_LIFE: 中外生活vlog
- VLOG_STUDENT: 学生vlog
- VLOG_CAREER: 职业vlog
- VLOG_OTHER: 其他vlog
- PAINTING: 绘画
- PAINTING_ACG: 二次元绘画
- PAINTING_NONE_ACG: 非二次元绘画
- PAINTING_TUTORIAL: 绘画学习
- PAINTING_OTHER: 绘画综合
- AI: 人工智能
- AI_TUTORIAL: AI学习
- AI_INFORMATION: AI资讯
- AI_OTHER: AI杂谈
- HOME: 家装房产
- HOME_TRADE: 买房租房
- HOME_RENOVATION: 家庭装修
- HOME_FURNITURE: 家居展示
- HOME_APPLIANCES: 家用电器
- OUTDOORS: 户外潮流
- OUTDOORS_CAMPING: 露营
- OUTDOORS_HIKING: 徒步
- OUTDOORS_EXPLORE: 户外探秘
- OUTDOORS_OTHER: 户外综合
- GYM: 健身
- GYM_SCIENCE: 健身科普
- GYM_TUTORIAL: 健身跟练教学
- GYM_RECORD: 健身记录
- GYM_FIGURE: 健身身材展示
- GYM_OTHER: 健身综合
- HANDMAKE: 手工
- HANDMAKE_HANDBOOK: 文具手帐
- HANDMAKE_LIGHT: 轻手作
- HANDMAKE_TRADITIONAL: 传统手工艺
- HANDMAKE_RELIEF: 解压手工
- HANDMAKE_DIY: DIY玩具
- HANDMAKE_OTHER: 其他手工
- TRAVEL: 旅游出行
- TRAVEL_RECORD: 旅游记录
- TRAVEL_STRATEGY: 旅游攻略
- TRAVEL_CITY: 城市出行
- TRAVEL_TRANSPORT: 公共交通
- RURAL: 三农
- RURAL_PLANTING: 农村种植
- RURAL_FISHING: 赶海捕鱼
- RURAL_HARVEST: 打野采摘
- RURAL_TECH: 农业技术
- RURAL_LIFE: 农村生活
- PARENTING: 亲子
- PARENTING_PREGNANT_CARE: 孕产护理
- PARENTING_INFANT_CARE: 婴幼护理
- PARENTING_TALENT: 儿童才艺
- PARENTING_CUTE: 萌娃
- PARENTING_INTERACTION: 亲子互动
- PARENTING_EDUCATION: 亲子教育
- PARENTING_OTHER: 亲子综合
- HEALTH: 健康
- HEALTH_SCIENCE: 健康科普
- HEALTH_REGIMEN: 养生
- HEALTH_SEXES: 两性知识
- HEALTH_PSYCHOLOGY: 心理健康
- HEALTH_ASMR: 助眠视频·ASMR
- HEALTH_OTHER: 医疗保健综合
- EMOTION: 情感
- EMOTION_FAMILY: 家庭关系
- EMOTION_ROMANTIC: 恋爱关系
- EMOTION_INTERPERSONAL: 人际关系
- EMOTION_GROWTH: 自我成长
- LIFE_JOY: 生活兴趣
- LIFE_JOY_LEISURE: 休闲玩乐
- LIFE_JOY_ON_SITE: 线下演出
- LIFE_JOY_ARTISTIC_PRODUCTS: 文玩文创
- LIFE_JOY_TRENDY_TOYS: 潮玩玩具
- LIFE_JOY_OTHER: 兴趣综合
- LIFE_EXPERIENCE: 生活经验
- LIFE_EXPERIENCE_SKILLS: 生活技能
- LIFE_EXPERIENCE_PROCEDURES: 办事流程
- LIFE_EXPERIENCE_MARRIAGE: 婚嫁
- MYSTICISM: 神秘学
- MYSTICISM_TAROT: 塔罗占卜
- MYSTICISM_HOROSCOPE: 星座占星
- MYSTICISM_METAPHYSICS: 传统玄学
- MYSTICISM_HEALING: 疗愈成长
- MYSTICISM_OTHER: 其他神秘学




---

## def get_sub_zone_by_main_tid_v2()

根据大分区 tid_v2 获取其所有子分区。


| name | type | description |
| - | - | - |
| `tid_v2` | `int` | 大分区 tid_v2（如 1005）。 |

**Returns:** `list[dict]`:  子分区列表，若没有子分区或找不到则返回空列表。




---

## def get_tid_v2_by_zone_name()

根据分区名称获取 tid_v2。


| name | type | description |
| - | - | - |
| `name` | `str` | 分区名。 |

**Returns:** `int | None`:  分区 tid_v2，找不到时返回 None。




---

## def get_zone_info_by_name_v2()

根据分区名称获取分区信息 (tid_v2)。


| name | type | description |
| - | - | - |
| `name` | `str` | 分区名。 |

**Returns:** `tuple[dict | None, dict | None]`:  第一个是主分区，第二个是子分区，没有时返回 None。




---

## def get_zone_info_by_tid_v2()

提供 tid_v2 查找所在分区信息。


| name | type | description |
| - | - | - |
| `tid_v2` | `int` | 分区 tid_v2。 |

**Returns:** `tuple[dict | None, dict | None]`:  (主分区, 子分区)，没有时返回 (None, None)。




---

## def get_zone_list_sub_v2()

获取所有新版分区(zone_v2)的数据
含父子关系（即一层次只有主分区）



**Returns:** `list[dict]`:  所有分区的数据




---

## def get_zone_name_by_tid_v2()

根据 tid_v2 获取分区名称。


| name | type | description |
| - | - | - |
| `tid_v2` | `int` | 分区 tid_v2。 |

**Returns:** `str | None`:  分区名称，找不到时返回 None。




---

## def get_zone_url_by_tid_v2()

根据 tid_v2 获取分区 URL。


| name | type | description |
| - | - | - |
| `tid_v2` | `int` | 分区 tid_v2（仅大分区有 URL）。 |

**Returns:** `str | None`:  分区 URL，找不到时返回 None。




---

## async def get_zone_v2_recommend()

获取v2分区推荐内容。


| name | type | description |
| - | - | - |
| `from_region` | `int` | 大分区 tid（如 1003） |
| `request_cnt` | `int, optional` | 请求数量. Defaults to 10. |
| `credential` | `Credential \| None, optional` | 凭据类. Defaults to None. |

**Returns:** `dict`:  调用 API 返回的结果





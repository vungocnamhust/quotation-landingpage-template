from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    prompt={
        "id": "{replace here}",
        "version": "2",
    },
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": '{\n"block_id": "T3",\n"task": "transfer_search",\n"transfer_type": "intercity",\n"from": "Ninh Binh",\n"to": "Ha Long Bay",\n"date": "2026-09-23",\n"pax": {\n"adults": 2,\n"children": 2\n},\n"vehicle_requirement": "7-seat",\n"search_query": "private transfer Ninh Binh to Ha Long Bay 7-seat price"\n},',
                }
            ],
        },
        {
            "type": "reasoning",
            "id": "rs_0ef7132e6d030ce6006a14641518c8819ab328e396021692f5",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "**Considering transportation costs**\n\nI need to provide an estimate for transportation costs. I probably won't need to search for files unless they're relevant, but the system indicates the user has uploaded files. I could check them for route pricing or any pricing tables and policies that might help. However, since the user didn't explicitly request file usage, I should focus on estimating costs directly. Let's inspect the uploaded documents just in case.",
                }
            ],
            "encrypted_content": "gAAAAABqFGRYX9EmPhCAh76sB5gm3ZyXhdiJimDifKtmxjLclXD3QVYNjcNv_t5_5pxon5AoV0G7nKcO3CpqpYZEz_NHLRaOpFeXwDfbTjd0CFsWSQqDyClzEG39A0eUaySL5144AoTIwIv4W7sHadptLTzUbqlgJLR21Zk7lFK7obI0jJbeTG2wMdH3PQkq0XU_udQB2PcrG5nI4TwaUnCs4LcHpfrxakvHMQGHpd9YkemC3xEQtyqnClkFltKtWQWdhVhkSKaMjKneWGbuqn8yFuDhb9YD_o4ML1cWXmL69AVK523sCpw4YmEEfpnL53Otx-R_-6wvLZpL609C7RDFJxVBhqvx3b71SuQ4UEcU_Ix0nIaXVRYBCbU-HNlIHdOQc8FCjjgaVPSQRpg3YcllboelX4PT-7n-rp0wft-MoxDBRXg0WqYE37CXSC9HWq49Yr0FG0TZrzZ4X35U_LspRYBQtMVDqqs2IlZW1Wo_tMyKRsMoT_HUvR6oLSS6rulvIjSJ187HTVB3okmsq7mAsrGzjK4gJIVwdeVbNR7erh0nsg4Wl18PC_sEgQuF1Hiy1MRHYbNPJLn7yy-2HeN7FzN7oXuoQ1Nd32E5ACDPIsaRxNYYJdQBBoMi6iTkWROGD68XiASkeCEll2PVspHoTfdSzui55WAIlfHLAmm5iYeHkDvr6zxTthKc5kIUyt-MADtXiyiQLffu2o-lEd2BM-xnw0T9p_Z41ylS2_XaxenUTeBNfKTGINcPXUbiXYY2meBi5ps29gUuPcwjiZMHLGgxuhjwPfY538Q1y2r97RFkzjhCCEMIZ4sQ0Y2wKKLAdExuJCMhASkcJUqGg92kyVZdpvkbZDfMoAX8KgdP3frd2YvL5HPWrC7-R2FH6p-2dmvfOwHKfpu5JiCEzuHukXjkwrlv-sibN_KAmcqYPkXw5n9SubJUFwGisyxQkjvsv8UE6b1zsz2K_fM7aN69oDkukha_q8FvJ1eeOG8dJdIMQxna8HdTBDrhApwGag3fybMWaE3QFJss6UP5YmKec5icZAky4C4_S8yyqIbaNweFuiCzkrQUnZbaC5IoLDiC5mi2KI1c_nnH8ygkV-0gLj2Fukj9m5LQXE_kxPZ2wBQjiJAw_ffbRQqGa3LDroDZx4H74lSPwJ5f8rerOZM5gLSbBb83NaPEqX_yYdS_WPyi1KtuMZ5199ARMuNTlMWGR1jcApeoR_QK2y2Mtnov4oDSlIA2netlYy95Ev1HPNsOEqOx3qAzOA6i7Aam33U1VLPmsBXTE6Df5hwgpG0nqhXgFnBfwnq0UhS18ejrTP31tRWpd6Aj5vN6GdAqQI5F2PNn-XdejsKV-wb5vU-a2nwZMfLd5uuopxY_bAYCEMe53d2FuzOr7N81hsWNWnJx9aICPT0GageNUYc1ZnRXcjSKc2FyL3zx5gZ-t7vj46XBxGDXz8zblRu9E5cER96g_lDJBBW_FhtqiHUD6bEaM885WT3mIA==",
        },
        {
            "id": "fs_0ef7132e6d030ce6006a146417e9b0819aad353ab0602ad25c",
            "type": "file_search_call",
            "status": "completed",
            "queries": [
                "Ninh Binh Ha Long Bay 7-seat private transfer price",
                "private transfer Ninh Binh to Ha Long Bay 7-seat price",
                "7-seat Ninh Binh Ha Long Bay tolls overnight allowance transfer",
                "Ninh Binh Ha Long Bay transfer distance tolls 7-seat",
            ],
            "results": null, # type: ignore
        },
        {
            "type": "reasoning",
            "id": "rs_0ef7132e6d030ce6006a1464184300819aadd645ec967248cf",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "**Estimating tolls for transfer**\n\nI'm trying to figure out the tolls for a one-way trip from Ninh Binh to Ha Long. For a seven-seat vehicle, I’m estimating tolls to be around 150k, using round-trip prices as guidance. I know the base price is 5800/km, but since this is a direct transfer with no overnight stay, it simplifies things. I should check the actual road distance, which is about 240 km, and see if the route details are in the file. Let’s keep digging!",
                }
            ],
            "encrypted_content": "gAAAAABqFGRYDOcoo7m9GMOqgwsXwVQkIEp6RP7ZU29N6RQXm18y_epnSDJoadmvvohwv_hnr3sddC3o65eCnHzOkCTN1z_zKqt1ZyB5l8ktNxVso7kMfmwyfdNrdf3cAth1NMuwbXoIrSzVPkHMnppFXUJZmVR8dLpAw68JZFpGp4u-3XS0iP-fUtO3FyG3MCETFuIDvezKrH7Q-BidYRepOuz0oVpsFnDhSepdg32jOTmD4MWvnQtnmOeFpfutjhYALiYyZ64cUhEKBwQCVURcBJonzaOwBEBL6CSmCWYhcqSEUT8vcdmreg5pktkYzGXS4lKdzWAAeKPMrLKvb1oJQZFvEnZUsYTsPBtXxQzGQNOWSoAM43GArT3am1JlwZkQ3fa7ebVFGzjA597oDGKMJNVp9-qf87J9cjMHgZCTU0JKwCSmAx5ZVj8kZ5hukkLtEw-Ws0sG1NiVVOO_qcUuUyc7rpUOAF8gjC3UPN57S-HM7CyI2cznuZQJNSHi5BHvVStZo6dBqF_9FFEmFX4U5aCN0MaVD5RJwJcdJ_2kZh2J8KTV5tyH07pV3FpdIt41vyoVr7k4k7whQmF_3C7zT_vCiTmS_pqbSqQvEeGwFmeUQGu8zP3aTiSmFkORI4YaUg8oQ5E_qO3vCRCxg6tNYAftcjoIZaKJa6Lk6McYJsNB8Zrr9WcnxR3rCB666CWjnTmE7WFFasCTSWYIsYflHnosekbzZS2wYSAuIuVtSU8NreP5uyuttJXUW716Qxlaq2QVssL6hN8-2QwauCbHqar7YJLz46n_P_fTqfwp7JcM1uvGlPbXgRE5emtg5FjqUaoiev5TGjMrTIHU5kv3H7T90JYX5r7suSSaT151VnMTMI5TJ6OcAIsI8K0dqGM2Tfsh07q9O44u5eFLBhU5CQHps2S3HYlQ4VfOj3N2ishwme82Bk3z-9CPeTZ0gPnhlZrEY6RyG3iu-d85Vb8faccjgzAJZJ5ucy3mxvtCgTfGhQkOsRbOtG9PBsdMACP0Va0HI9U_Jfv_primjtK1RYtjw03Q1OsvcK9OvHyRvR7h07kMP9r0JyCvjLtBF12NjnrXVfeptPZWYVePOMoqA9MnxWo7eVX9xSX6hhM3v8jnmPU3kp8rRqN1lzdiuPw61gLc63eA6Qtg3Wlx1laiaNfGMkZMJYg1b9mp9qdaPTO81QjZm762_yUsXwFBwFlbxodpc8QzyzMiBD2a89dVe-j0sUKA4b59ZFmxzVj3eGpDzK_FdjViiC6nDbV6m8XtGYf_iDoKrwxsQTwhn24LoXwpIJyxCwPpBX8BZQuGYl7tiq0EBLBn_-2kb4f8HdCqh4f_AkmTFkokhthY8XJCH6QV_QyUqzrUWbJwX4Vi7ZeqNW4T6Gt7mi-Ldz660n8tJnVWl04-ljnd477P1PyPhOCnYvtXYqs_j-vwYM1PX24ryQ0vI-bpoaH_x87zg26DoLTSc3eDkKs0rGq2lI8BTZWjbi8HM5uYrVuGWFBfDDM02M95l2xviLeakV1eXIHDCbh2ZoqaTY7vUNmmdlcIvoCupaVpFRygqqnNcu8E7uZvTSjLXh0s04C1k7lRHnem99gDzbFHTU3G5tJxx2v1nYCspMf7uxlClUK4PQT4fyfOPBZswD67Bu5JLgatWe2HHnTCyg71SFva59-etYKKewW9arXgPML176nOjPnjnxGSj8N06ATkwvZ5g4GjfkR2L-0fs1pPw-F9OT0CyU8ipTr1LZ3zXgJY9eyHGKFPV1XFH_9ehDK4FA4E9ITMhdoWEy1prAyMx01zwmTpH78HmFxrzTBuZpWn0FcxtJQ5YYyxWiJVKxrD1CtrOHaOlStst2JfbsB1flrmeSpdl88UyDuzKnQd05FaDDz3dUwIFTr55SyX5zMUo4cZUQ4n9rvKjyBqc5wx37V8InDkb2AiD0UY4gAfpJQ5hF-UTOWbOA5XmnUZOYW3uGkS5b9kj32tPlbDD5ZfEiJqu-GGo43VHkuwbyt3DJZIr0To5GZ23wrGr3jZi6Gbknlqr2UkNI5YfqaaS1KHvct7e81iJtvF-vUJJyFq2Zt9iL9CUF7lYbrk4TEXzDY3bdPiRBf6yV_6Ub8ihF61a3K39UYDvZrW78eUmbIywz_ZRIddxP-P6FSRF0ERoQDWuvor0D1IudzOScAjjIDQNPSSoU-p-fpZfSc-TH7HMijgS90iGK2_D3OIfW4YSEsCtgaiPaJ5ybOdoaBwpa49gEoTvT9_dRnAXlqyVrnynSV7n6KxhNxcT81jWQtTnfnQOW7bPOT6tFB2S45LGT-RRW8qOIu8DqS0t5OHZBg8pilYdK8efyQCKduCX4UNKHFtgTrRDr6YXZA6Mq85zzIn5K--mXWd6LYBZi1Et5s0yAPdoJQ4f0yPoosyfhLjsLJuqwh6DNGlvs0p0lrlHTSO0F9m27bNxvwGJyf6-YtPEYAQR-vhTsV5JJ8rDATZTUWiaXMG7-C3z_G5KcsuHUrwYXuYyUdgQM-Ua6LcN3iYyVdhxv4kzz-NS0RxPm9248Mw5rBY08RSsvqyrQ-dK2OGkXXa2IgZ0yCkZvhR134lj_mNGitj5Oz-xPg2Gy8JXEBZKWA7ZN7fSFKdgxsYPZ1CarmXhElVzS2jz1NtjJQqQJpZuV-LC2d2Wcp7hVx1E6XVGYPq_CAc31zAnaXCd9hJZ40czWRocin0nbcs_j6MsYGCSL67zf50ZTYhlng72y6xC6XsqoAQjE1QeMuV7WliwEfzKwJZ-Sk-aP_-6IR9UNbm9AFXO8Gpf0DD4rDnJ1zM-N0oaYML0qQxQ_x_cJQJillTgUHyEgfePguKv9FqX8qiEGFsOrIvz8rzcUhSHjbfA-QyVaBxPx-n25titlomc6XIv1t5qGUdipnKlNf9sCCOUf0RkV1xNQP0szwPgxuOamXtNl17PhHt6pTR29P3ymqF0GjoKM6nS3GGu1YTQq-lNXp4Bk6yJLHraStPjMGLAKCUqSZlkVCsG-E15n3TiwQ0s_4rAjbz6BicClTCRsF_h3hsJgbTSNe3CQ4-fWdc0F2Pw1vvxbR_vwnY9kFEofP8uhi338HDpz7dvjKy0vn3vsXocTYImDDmb_Yf7QAKe1ptXVKc-NpaP8qgHWB1",
        },
        {
            "id": "fs_0ef7132e6d030ce6006a14641ec4b0819a87e61bafd3ed17f3",
            "type": "file_search_call",
            "status": "completed",
            "queries": [
                "Ninh Binh Ha Long 7-seat transfer route distance",
                "Ninh Binh to Ha Long Bay one-way transfer tolls",
                "Ninh Binh Ha Long Bay transfer policy 7 chỗ",
                "Ninh Bình Hạ Long HN 2 ngày 630 730 one-way transfer",
            ],
            "results": null,  # type: ignore
        },
        {
            "type": "reasoning",
            "id": "rs_0ef7132e6d030ce6006a14641ef558819aaa453490f532d70a",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "**Estimating travel distance and tolls**\n\nI need to estimate the distance and tolls for the journey from Ninh Binh to Ha Long. The road distance is roughly 240 km one-way. If I consider routes, it could be around 240-250 km. If I take the expressway through Ninh Binh to Hanoi to Ha Long, I'll need to calculate tolls accordingly. I estimate the one-way tolls as around 104k from Ninh Binh to Hanoi and 255k from Hanoi to Ha Long, but there might be a more direct route using CT01.",
                },
                {
                    "type": "summary_text",
                    "text": "**Calculating tolls and pricing**\n\nI’m figuring out the tolls for the route since the toll table shows 208k roundtrip from Hanoi to Ninh Binh and 510k from Hanoi to Ha Long. If I combine those, I get approximately 359k for one-way tolls. But if I bypass Hanoi, I might still pass through the ring road, leading to total tolls around 400-500k one-way. For a more conservative estimate, maybe I should consider 350k. \n\nI’ll calculate costs based on 240 km, estimated at 1,392,000 VND for distance and add tolls to get a total of around 1,927,200 VND, which I'd round to 1,930,000 for reporting.",
                },
                {
                    "type": "summary_text",
                    "text": '**Determining vehicle type and calculation**\n\nI see that the example shows an exact figure of 5,295,400, while my calculation comes to 1,927,200 VND. I need to ensure I\'m aligning with the requirements, so I should stick with my calculated amount. Additionally, I need to define the candidate vehicle type as "7-seat" since it accommodates 7 passengers. This helps keep everything clear and organized for whatever needs to follow with that vehicle type.',
                },
                {
                    "type": "summary_text",
                    "text": "**Clarifying response format**\n\nI need to start with a human-readable breakdown, but the system says I should also include a JSON object afterward. It seems like the format for a transportation cost estimate requires both text and JSON. The developer clarified that I should provide a breakdown followed by the JSON. It feels like the final answer should be plain text first, then the JSON object. But I have to make sure it still matches the required schema.",
                },
                {
                    "type": "summary_text",
                    "text": "**Understanding response format requirements**\n\nI usually only need JSON if the response format is set that way. But here, it seems like the response format is a named object schema rather than strict natural language. The developer has specified both a breakdown and JSON output. I guess I need to first provide a human-readable piece before following it with the JSON object. But I should keep in mind that the response format might be mandatory, so I need to see how these tasks fit together.",
                },
                {
                    "type": "summary_text",
                    "text": "**Considering JSON Format and Citations**\n\nI’m thinking that providing a human-readable breakdown in markdown alongside a JSON object might work well. It could violate the schema, but the platform likely can parse the last JSON. I'm considering whether citations should be in prose and included in the JSON notes. But can JSON have citation markers? I guess they could be in string values. I’ll aim to ensure all JSON is valid while computing the precise numbers.",
                },
                {
                    "type": "summary_text",
                    "text": "**Calculating Transfer Details**\n\nI’m making some assumptions for the transfer from Ninh Binh to Ha Long Bay. The actual route distance via QL10 or the expressway is about 240 km. Since it’s a one-way private transfer, I’ll bill the actual distance instead of the minimum 200 km/day. The vehicle rate for a 7-seater is 5,800 VND per km, and there won’t be an overnight allowance since it’s a same-day transfer.",
                },
                {
                    "type": "summary_text",
                    "text": "**Calculating toll and VAT**\n\nI'm assuming a one-way toll structure. There are no surcharges since the date is normal, but I wonder if it could fall on a holiday in the future. The VAT is 10% on the subtotal, which I've calculated as follows: base, overnight, tolls, and surcharges, leading to a subtotal of 1,751,000 VND. This gives a VAT of 175,100, making the total 1,926,100. I’m thinking the toll could be rounded to 360,000, but using the exact figure of 359,000 seems better. I'll stick to using the precise numbers.",
                },
                {
                    "type": "summary_text",
                    "text": "**Considering travel options**\n\nI’m thinking I might mention that if someone avoids the expressway, the tolls could decrease to nearly zero, but that would likely increase travel time. The current quotes I have seem to assume a fast, private route that uses the expressway. It's interesting to weigh these options since while avoiding tolls seems cost-effective, the time spent could be a significant trade-off. I want to make sure to communicate this clearly.",
                },
                {
                    "type": "summary_text",
                    "text": "**Analyzing transfer distances and costs**\n\nI need to clarify that the distance from Ninh Binh to Ha Long Bay differs from Ha Long Bay to Hanoi. It seems like Ninh Bình-Hạ Long-HN covers a longer route with two days at 630 km and three days at 730 km, while a one-way transfer might only be about 240-260 km. I’m estimating the actual distance at around 250 km to be conservative, which gives a total of around 1,989,900 when adding tolls and VAT. That feels reasonable!",
                },
                {
                    "type": "summary_text",
                    "text": "**Estimating transfer duration and distance**\n\nI'm thinking about the one-way transfer from Ninh Binh to Ha Long, which I estimate will take about 4-5 hours, covering roughly 250 km. For clarity, I want to be professional and round to the nearest 10 km, so I’ll use that as my conservative estimate. It’s important to note that this distance includes pickup and drop-off within the city but assumes no local sightseeing. I’ll also indicate that tolls are included in the quote for accuracy.",
                },
                {
                    "type": "summary_text",
                    "text": '**Assessing search confidence and options**\n\nI need to set my search confidence to medium since there\'s no direct, published one-way toll table available. While I have solid distance and rate information, the toll estimate is just an approximation. I think mentioning my assumptions in the search note is important, especially since the policy provides rates and toll segments. I\'ll include a "candidates" array with one item, but I won’t add an "avoid tolls" option since the user didn\'t request it.',
                },
                {
                    "type": "summary_text",
                    "text": "**Crafting estimates for transport**\n\nI need to prepare plain JSON without code blocks, so concise yet detailed is key. I'll include my estimate notes, mentioning there's no direct policy table for the one-way transfer from Ninh Binh to Ha Long. I calculated rates based on the 7-seat per-km cost and apportioned tolls. It’s good to ensure math checks out: 250 km multiplied by 5,800 equals 1,450,000, plus tolls makes 1,809,000, with VAT adding up to 1,989,900. I'll note that the children count doesn't affect vehicle size too.",
                },
            ],
            "encrypted_content": "gAAAAABqFGRYWtktbwI6RMU1kof8xp88UU75z9sOwB7DszlVoMHUJmA-KYfviqhqjoj8qPu0FU9f2agTm1B3EBTbzD8GZpOTul41uevt5hAYCb2GbKtY1IkU2DK-2PYWIy9rVyLOYQOdosUWwAGzOMJbLti5lxbjX0DYzgm0hqxW9cdyE3l6xYbKOQ1PWlyCTKQeu01LIA-r02LfnrwW2MJBQvjnu83dS2TS3E7Y2TTypFKaBKOnqezxsXB5nOjyJN6prBmhVRc0KKgZ8taO4ZhMI_FQ41aNRp1imayzNua8UnYTjayhkflevN8ugVpIqh1QttNcPuD5HFJpFoYfm_z2IvlsjWzNvY5eZBljMljhpump-_KlkXbghkOiPUDsvqQPws3Hms-GKJt4I4TdROjqDVFYn_Y0WhFbMTlBwNs5YYZ_hqYWAOqAZoxXJUBuv3AsJrbetVAGQO0MY3PUpv0Z-3QnRwgZUmcjqijmuWAUEkmLHH032kHnCNU11QBxn7nX5SARpmdtpz16VjBgRrMFuFQKrPZyGk1H7DXsCt76SI5ib3XurqMG9MEBKWCHp7TvjbcAJrir6RXRuMiiBU_ymPmrkuPuPqP7Xm_bE-OLIMs-x0xG7oOk25_l8SyqJSmpNp4DaTvjrrwExoyyMOVaPganfZyOmiFIzTP4_luK4tMzx5ZWIbYa0bW_U_cGJHCAUsZly4pDyzozAQn1oJcaA-8B0XoCZyb8b8FST07Dlcsu7GQoAe_baE1fdZtYtOizC5A7l5bc69T33Y0Y130aqpVoNmqTGfVaoj4bZGsPim_AGeOCBBMyb_ldLTAx90KV67QgXBlvBkPzuxFHe_NK-tB7XHYYuZ-9SV9E3iwb9CFyP50FxvNnDoH9cjNc45Age7jL1fnwLyJBfa7w4lVOWYFQKx9w69yLlynL_xok3kKEhkyrnrD-3b5XEzg9p8SMiSjfOVTqbM6FXpZaE6G_uqU20t7JeCQ3wTXtzDTMJkigXVU3DnRmx1Ee2PKgh4opPyLBQAU-g9JQhT9ELSK-un7zLQGyrjQ-gdF2nZzJhoXda_avM98cfphPjcV3PcLi5uo4t_FeWtuzsfv94ycqvoOqFbcV2slJpR262yppA1KYE185pyBgcog76nPSKbPEJjySV_h8QNscmd32G6Pqmvj-z7yLAB-4Vpy1wdBXq4iMcrDwR9JKEWeJ3aejnrIEUu7X55zlcs1GXkLY2a78omAMd7CS-qfvdfSD_-1szTFNJXNMFGDeTSf5ZWcNu09RphKdP6rYbpu2sDIfm1RSiPLcPaujCdjQR-CX6sMKmZM653SwLTuRrR35kyTGkBMcerOzDNhLPuRTcB7AsZ1oz832OmJxXmlzgBSRFOyUgvphFb58gWU1IsQAp5n2iCFdruU0g_SdzOnE5WNeWPoyZXUXnN3gcArCAC_ukOrGqIn9Kdrxss6E9DVGbXKrOhI89tz6hf5-4-u0r2fjM0IQbPxcG3atWAIE22L__PYt0l8877TJDYwu3gFFXOZupp7OIkeGIb8PEnDv3ztMphqJft8xZZ53tWu2AoqXgYnunW9IkcCZ83QpcgAEYB7Abyb_QFAoz7PqwF6ebxU4g4kHKiPkdsJypnvdcTFasxazb4kv1PQ3jRg7JVVzROoZ1CaMnubsw9Kp08wq2VQmEpH7zc5zpCsJ1MTbn3T5pInEtQZplWhnQaF1DOQx6okKrJrT5YR_izok3pKtMcXkBfAk5RRWL6S_vO_idlU9DZaT22g1caWtODisnQWn4xnnW9vjZKL3UKggtRHYswQL9eQPiWevMpRYAIIWqLyHhrqW3nAOp1HRJjM1BUtf7n7WqEdgxSyHY-P6dkzIxYI7lwGq_tQW0MWooQpPGMZRFuMOq_zLogIgHveVKBQ1zIfmaEW0iMMaF3OwUCNBrU9uqbn_e_qAHApz53Mi1nbez69Zr0085j3QEVWrabW6zA-W5-YIaGKdhZfP6rdr_5eCxvhG5RgjbeQD6YUP34TjTrVr95bn9eXHU3WWOXb9_dRDPO8th4XItfHpdyFhm2iIcIyPj9Smc3kn7Ez7BKG2mVMIz8_O6PvNyjRrqE5O-2o2icEhKRLApi2fpJU2Nn8upCogDLVeFiRFTFxzPBL8UcJLKjC5ALMkFt2t0zZJ62-mj5OShx-fSLkZVpJahCs9erH_bmjCKxGD2qUNtsAwN8mJZrnu2Cc95fhNhFFzI7pXHACH8vYGsQAXNGpWLhV42F_seFMOANpDOI4y4r-o9IjJPJyR-WMG9cB12gkKKJiSeMFGMQt3xaY3kz_dJV5jzj4XuBBLSVMDvlqQp2U6F7L_uWUkLepLdqCwwifS2Yf0vpAZrKbkhkhypzV5caPlWarwROQChcxrCc3gVLOoqgOdFwq9M_tAsNjpHbC9U7PRV3owqu7f_ipJvNOHWwkZ796096OErM5kG5N6ukKYX-58ePAvt8Ehxq2EpAHbZ-p0o2XDftRT9t5EyUFP8EiDTDea6I6EgLyVOaY0kGmf5aOopm9iuR4k2t2r5ak4QgQfOYtggCDYyFUANy7WiUQnV32X5HLmopVEeg0n0IV5S0II6D3i5SFYNbJdeGiSrTfDK1fbNPs-T3xztJ_o8HTN0xhGUThx0o7AT8gbGTdZi05thTLqeWZY5oSZouGQOsJgyZXiCzK7L3deNMIk4OZVTnVWIIzTWGzNSkqeik6EVYlZKbVsyUvK9us-4aOZCuwit4sBDZYVgdlBBJGYTjDzOVwW96DEaFFXOoTXo59e39vinBjIpPvzaf_ZhNsyJ1FNl2F6QBQBXt4n0sInjeUR6X_mvRdsLqmHC-yFkWghVF9Sh4yWYzeikIVDS0IKDRG5S8fL18M8D5G2LOVFe3pXgqldL8VzVTOL_8mTa26eOJIOoOZt81l62cp4zV-Yl3tiDZqKwt_hwU2CO8ZGdogAz5BauesCz6dmamu94dO0_flmh56D3eyD9I05F7hdFbg003yec46KOdQTVY_xR83wDHRtt3_ICwDI9e_ShpTLbgtjy_EZwLP1jte-V9ouE5HCQ-oRzf2GxKWfNtosLDplvaCi2hxwU636HkwCuPC7OmdnFN-jSuKGrCjTxp_m7NNnsHnlS5AxtOmArjjze7LNymtpsaQ80EQy3jqsA9vHI4GuvRZjPo_oFtV7gEUdNb3s9c0UrqnEq3LzvqEf25g_0DGMHcvnjAEw6MRbVahBkZ9gJqlGS3nv9J1OghnVTzY4_VbHGLhR4afUQs3OY1OXGopbQmnUGeF1aaxu6S5HwfOjhdF_1nfeHMuOdxLWZixnFHHmwfo5MthHRCKp0NfsK6FRN3vx1qMxDj92az26rwuujzfwbJa7xDyNT7CWeT3THN-hvIxUDS6ysVpOFErMdWO4V_kkXynVu3NDpLcwnt-RyP127-qqgywin51e1X-_sEbfWgSfOSlX1CgXQv_l0jimDyBSDgZC0Joec5mIczgON_k0Dlyz2jiJ7QlMVHK-Ufa7oAa1W2rwHuu1pRprkF97E35wqejcI8gn8zkrqiFaAom4zsR0qjPptnYB_2HxAaeL5rqBQTMJwLFtDal1BVSCrMPTzoIY9MfqCPol1KVLvnhijAccm2aayFWUN-n_jS9DVMtl_PuX20NVyxFrqYckNhi7prsQZn8i-X0BaTwYXgG7lVJ9FkC0AJsscCWPcspMqZjtL62SbPBcUl2EzIRX_XY9VYIFbZENVaO06iaxSHz8duKuPOjtjkzieXlWVdGyz7ufiJsg2Xo3_KcuylFsKPaWm_jz4ftq3V93aNOEIgdTij53zEniDxTI404X1mBfkzdER8qvqcxSRFFFZA0H0wD1UfeMC_y0NpnTWuDTeXDsWahKu0KbpniK_IEVJVwlH1bsJRQ432cyjar1UDeoBWxCHo0dOAjI9lXbOqV6a_vD-69fux8hB9ApsmvWEwjQEqL2XTPvckMjLd_SzPjgArVIrL2YDztq5ds5_EgxDjHcb21jMrG3axFqgY59zVnyMdJdKP2VIIcrPqrWvrYMEV82NZfFpjXKN-tyLrPXSMPsvE0kocvUqCdHbBtF2Sya3Lgjs1pM0hpnajlNF3KkPItZfvwKRvg-FK_bYT74YjAEUre2OBGfb6xVnYxf8LPDzxbZorCdpX43i-XBJjbBe_20PfXZRYAWg_B66jEsHoB9w6Va_XdOWICsSMqX4ZXzTQQFCvFYffZ4k0qX1leYr2WlLBc6nUiNybmj_EVqR0MgbrNG02S5tbDvQ09MRIoP1ZJYBXDaAumrKbUG9JuDMZsyt1IxGYUORzqooUn0uNMZuGhTTDPik1Dovco_GeHJoah46zwgwcvj-V8oWZPWXVq2Wezq7gs4288ZrRq0C54dUoTxFHTFfm2Y0fq0yTBsFNMPUWK4V-dKmSVSCM4uH6SJmJmNfQC_Ba8Mv2noAZeOtOkL-ORxakdRJ38rs1oAwG57knwXDciW0dhmww0mmk3vK3isnCHsO9bFZ7QoJhsBBvrZyxkVHdkRbHcSJCZWzz391Zxs3p9275TcpDv1qzegPAtLBtdF2rD1-jpxZNNtWdWEpPbeuLBrq2hOIFX5gFAJabICNlIoBZN8tuXN8gKyCJSLuQ2w0WQPQNFlwoAIidatcSGbIcoefgvZiIPWC_Yl19Ax2VfSQ-Nk_8nCZB60CRj6ypGxqk-2RVDFeNqNogGiYNyA2ayVyiooOMrYolA-NNFYebIjBxlcVrh5BXwU402gPZlSF7dcWPOZj_eihm-FqfKlL6wHrN8-EfCMwvznvEdm4O4Ro89qV4jUCkSfeVwtHHoNxI7WMBPTL7Xb8jL1xdnVRttjL2IXklWoMszbRVPsyLR81QxRyEmu_Cd-0h0S2u_l6F0Ne_5Sh8zSJj4XYd_zYy1S6380UlMHHwhaTCMevuv7NRr7rsFYm_bgptlEjMtDiADETo_HC9VOJVyxrWB_Cdav7TJJDzG84T-mE24xIfLreeqbW4TEBLkuHVnzIezamS3e-8sBqvjQ_zKwocE2DcxAYaIk6jjin60vn4e-T63TsYnYVBnyHRrKFGLJMHkbh2QNAccfLBpCAYQINueMB36b-jJMbof4ihqg6qxi3Awnu7yhRwdAFNBRScJZDVcIbdEcKmhT6YJfNZj3Ku7_ErDydO0AzkUgZbexpjwS5mkp4XBuV7UVZH2mb8_iyegeR2zsS5TggCYLYe5lCTbOoYlOP032NbJk2Oj1DwD4HMGpFp5wnE9ZgnRahuLHtp4QAg6zBJ6dfeZE3Deu1bmHb8ktaXsl52hO1Tzx887kf0aaORHURhXWmv9R80GOUYgOBxUUoordBE1mRplnStoasEwMaV3sQVQqb3G3QPEL95d8TrtpVBpODM_I-VojFsdDbcaFgbPR4zNp1TkDNQ82pHbLFQIP-gUrTahjDE675IS-SIjUP-YmfeCnls5yb_Sz0L-3fzo57EDlvLljo68Uuldco9hq4TpPCqXHsNRU20vu0dMzbSqt8Cnh-SsEHdvraGzz6QIHrC_r8AExuDaC6-NoKEjEbrnb5qe_WrynLXfivR6dP9Pp9krrZDpPg2RvRIOSoWcH_CS8txStmuks_QfhK0vz0AVL6hEB05DxV-BHc7GEWwd_sIkcGdpjAAv4OdEl7tHRip3DXYbMXUYDLTuS8UdBUeWRdYjdu585TQdn33frBEBCds1-zrEVuk65LywPb-44ZDihqsBSEtKOXn-murKpMIJV1qsAxgNLmUwYBKUxCmmU2T18pk9ATu7_QPyZPiQm_821h0Z-TSjqa0F69C6d2B_Bofgj2BYgGjZUU5Gc9Dz9t9fxGnR7N6A9bZ_5wrh8clT_B0WlXiqlXHojAJPARF7-_3NPV7_StQbfo44I_IvPQ5p8M6u7-JQxBEKby-6hFhbrMELTw9Os4mqpgEbJkkkrCb6M1Agoy9m0Wfs2E18JtR4oGL39b6KXE5w6Yu7_7SzNy_3O_chnt53YkceUU1A00ERjOpFEWuSGtlGYNHLijyH4KoCk96T6_dTPH-9Q_XK2CQcqLfhK_plRt1q0ENbl8B0TZ4fmDd4Tu1wY1GPIOtpf1rCzYko6tiLTngCH6Wh-Hun6SpEZPYfwz-37Sttkyzk1Z3zLGyq1p8sdNNzqAGC-nXy08QtBkOD0OW7wh2rLi0-Qh-t2-YGAIV5wSRAPYar3UG1sU7aHi13u8nrasYqGoEXIDjPIRSYacvHr7OTOOIzhNRVSJq-VnyLGwLNgzYymz8cz_m9stjye-lYpBSoJVFvfuqiel-fY_YKn7OlwTAp67ccXweRtmSnl_VZS1-tQ6Ogo00Apoc1Q_p_VGEZ7G1RthfD6quDHR8-yn2mi6I2bQZXoQgLzEkvToBdE1bkuLhhfBJ2-XE3FEQbAdj_ZfuOo_vd8QT2ekSzab3X9n9CclsA8VhN3UIMS_VpSfrNU0H6nRMV73BJj3pO82uojZ80YSYIuXHHK799Th-_PUUDME0DkEH9Y9JoorKR0fNwTpe90MEJu_pg2TlxCSW09UmJeZ2bS4nqtrAlQjd9dPrtRu9TMJCHysxIb5JI2IFwAQkfkslTN9drFvttsmWLZxaBtEz7KDJb0NDFmvR05PUWh9Ahvj_RGys4RsaUXlpcdgkBEHYUNP3_3fJahDMWnSvI0QUQGcKQDRW40jhb6dZ2Pg0XEf83M7KFZbFAUtCOFHXPV5sHW4l9ygt4Xl1r4UnI6ly0UAgyt19lQThjJ0Y7M9kn62-SC_Ma7LCaa3Z9k_2XLz5JJ7Hc_dYF2yHp-VbOE2ZudtD9_ndfwvOMY92jD7VoCVI_Y0_acPqNU4kzut0CKqbsCtnPHE8OxDG4VeQB9-UYMmpx48hqieaLMnOgVfWZ0fqJQtnR5FcZ5hSupGHi4MfjPrcPPTSRsRZZRmQFFuukAWoH6zl3h0vmCgMQw54pb0wM6IKQYqT6rCqbFyefMQixC15lTiEsm4Y2rAMpX54fyrfiEPSt23ylMnGQnXOOhdNhxRB0vxpWZ-qArx028rBAV1oazwLUk5Rpp7_KPyZQzqN15ZTkLRN9MdRFIUD7CYBkz62qUgo3rkvP-A4tNRLZP_ttJR6WaRcaydCXsy6gfn85c_ZvQP4Pk1F5w_iu8rMlSizk-MeNWOijqMr0JTY7tmpZdfPDMwwa66PZtHTIn2cBiL2or5iq8i4OVuW4DjJceBHqZkuMD2CL8XjKlTiyASM63Zz53jIw9raVetW69k1zis9VoSmVg0g0cLB9Zqzw6_fzLSxf9saCZdIQR8F1u_cppTzcdg0o1QYzD8F3pnMPCw9Pe3YtuoJGU5LGaH0nIIotTlJOddQfeq8zmClmCyN_6JJtk-FjQ8IgalnVI29GIcse0efV63iGR9KQDpOSIHj8WvjwwRI0N2z51JAX4vBKAwCxb-xd6xN1MK_ZEo0ja74fTqsE2B80cCxw5LGpwzIUS9VLNWQ_i7Negxxul4dBdLOM3Q6wmrzzGc51bJ5HfkW-4Wi-sr2CoVFsswRpjLMGng7DSyCWrrVwH5IoPZMQTg9_uIGpBMcPar-FpN-ZY6b69kwJM_tS9Gp_o5VxwnP6LlHOzrXgj8aPgr0bA9ClzYJM63BOdWWJ4XlKkzSFmwdAm-0v7k8qizxK1TnPajhjnCAL7bCTZS0vjekNAVArnuwVyxzIcG8kG2_-6lBXUIBbzUrVng8b0ThtmgiJuuUE8DYmck-5R9_QyGjsbbu2ry4TF1jYu2ZG3PPbrzaop2JCN00AVavqo0V4AZJpD-4LVIEFLdlBDZouQqvjF47oU1uNckLyOc5fn694ZbCrzIQNjVzTPCKfDxQuii7hx5W9PDYA4MFSPJ8J1q0EYFk_hgx5PcoG0-OrYvRcuw4A1U4A68G8at4V9hT6ymsImgi4lUsOQ1sopX2bp9WCfk4O3Zw-Mvzp2O8BtWrk9DO-T0-XX7y4p50tBeRSJ0yKYqpmBNkCZoEgr60o2mNCtGABWvaear6fnxF7Npz01I8O_MsBxd_QrlNPUSkzUdjrp-I0OWUUzGtHy8zv_jWFCKcFBqz5d-rb09UT0HjPAGI9B3jNWymQHbQV2lWHhXKj0TFCwH0PfNeUU13yRSqH4ULZHuc4dnKAqc_WwEheGL5t32ozhwRRixN6wxnxp1DjVZYDS4rnglzG-kS2aqz2pfi3RZZW7W1SZwEElmhqmnvkOYVSw_41x9mBYqro84E793PavvNGdWNWMXlSNV2n48-A6uOaZx9kEcVidwWZQf-aaFDgnGG_MMNXTi1oWwDOn-FDYbccGSjv9LDasr2yX2yS_n2ORurG7v95kOjGDphYwt5RlXsnsJBnuRLICFf7mjTeYaPFvSEcslciupHDRBP4lknqOkCbyvB_dYv8Mcao6B0sxwMGDhUhYVyNKl-NzzJo_MSwnUisJAZs0oo17keeAlQgqWYDK4WG6ochLw1mNX-Knpp51mKU4FN68MumAeiClc0Uuzj8u4G_NyqQ44W7L2BRF7HfMohpBtr-NpDWhxDeP3s8AqbpqbNrcwKmyNq2_2bn4UODW6A3ulwqUMGOPn_NZ09k1thHO_UuVajCZbWctRocckR3qHud6Z4A9-exc_a8cnpXC-XlO4sJjlvaTGPDdiyHzaBwj3j8M2ZnccC-C7mVbuDUxM9DFj-7LCeVUya5nrPi28UBZYcRGqeX9AGakVS8cnE7w7F0mhzZDuiHxhe9_DlmVdIce3OReCthf6bPGPQ1yuh2uJPET8gin7BqLCWV0PnX1BK4hzUHEmEWd-9OzZCVmRXmFPadaZmZOVt_tVyFlyNW00ec3qQPAMrUcV5fmPEjBInplvt4c8SjwVRgf-msHrWHIUhBBDAtoRT_905-9EbVMNNJanVQmIz34dmVL1ZsZMZf1f-3zgfUVEQlmUHeusgZGmr3B8oAAxe7NE80uhNjyo9BIzonQj_zUHHyfNZ_YzKFI01t_-nmgqA1RpORJ5J1tNPue6SWtVy4-rHue6JzbOHmhtFmWcYHmtV6Nv_4aQr-TqlUYyXWbayqANxiocuODwbO4NuHTQgjUq8IoB0K4eLqGpjEMiAEFlUFPXgKxn0NvFp3YfogflVIcA9XcTeeAbRlZ8DjCg0LznAeSBC4bPqWrcXAgvwb1QFfJkDI3dFPhcFaQLzldO9QLlMy4Jmh0zJGgoyBxqoGCgTDkc7yVratbajN_8SSaMUHDvjwAfWCiwmRwaBzUNV6XnV_6wS1qH_JbCrNp9d2dBqxlVTCoGeOc6N351V4hiJaW6mqp5vGvIJNNwtqYRjCkbCwvbmaKxQWeVlr-0UKf3pqE4_UuJuWVqujRYVcV0ocdPJNx95l2dRYTir3Aodv_KVuEZILcu0KAPBUWaLsXUlErDlAkr5gIMPFWq_QCi6_pmHb2rfUOEtdQOAkpEMehwpMQGnDYC7-zsxJ_rbD3cqapOfC0Y_H_vVATXhVC_zjf5Il23wEcLExbY5_VVNCfXIMuqwv9Xm-9PwNQo7PCiR5VJhoASeOZg4Ni8WcK41pyk63Qx_p_l7LRqF2e22cYggSvA9ZCzeY-WMbDIWnGxtNJrAn73wXVRZ-iYdTYX8C1MoNkpRU-LuEsrYn-cWl8o8qT-4eAtQ2q2pGJS9JBChQANCF8M9gknkC_tQz_NpB0l2p2y4RA7UdqZ290Fgio6xjf2guC0rTUnFo57uJFamdW3dZG-BCiKqubpZQEPKKYfOkBcCfvchNU-M4mGtEah_kuA78VduI5yqdo-ZamsqQsBDkvj_9QU3JU5vPcEZTAWTvjjDJtTK42QzznZaA7NIH1V6W_SJ-k2T3Fpt7HTAf9bN3wlUF6D3NXt5zET69ybYdWVc9lgcMlGuCMex7ODJo_T06P_sEeLLadISeJDMLVOCucnz13BYZF_SdynyuKdTN0UyBWT3x6ViNFAfRmPiZmIHuc5xZgx5ReRPQLjaOJIMReof7aug24um6vlOeqA-QPiP0vvugs0YnTsmdraESSMlI_03VwjAWpsz59-b1IqpAGTUyWzH3sowLs2xPhESpJ43frEmjsEUb0fJ4DuIlR20jch1guYysiTiXE8bAg1LoAjvIl3gOcYyW577bPI-AfzyJSUdG0zz6KVq8Z3MOqpI7bOhY0AJuhGYNoU7E8td1wTw5MUsdIHDaYryJVyfYeoXveGPPw83ahV-nL9z2OTWIm2tqdtsVD2QLgaCi_U-_5np_gh3JxXS7fh4vXqzjiXiso8gX10ZFhsffORgHxXwZj0gAb-B5fgpwqiUfHOZiMGBWT7816zlt3UxFHS3pCQ5qHqTPaSJjf3LZyCpj350C-_4F59PgViaqTbeoW-WdaLIkTJpIfczXvNeCO_VmmWi9h4KadMH33CW0c_f_xczfB59_HXff67D96AQYRvfK-Sy5tD2IFt6a6Am69vd_zlXCNnlngH7-l3dtl6ToMwgpiZNUeZ0mCYD31HPlgZHSy2LY-dQy1kOcaf7wYboaII06G63QYFYDi1tVAKYmPmKc6xw3O7JsRqoxI-ky0zq5ffgikc4PownTk2W1DS9VHuKTQTmuJT5Sl23ZBCdEzIktJUcMhg6SMfTfrJlV9ZfyzhXjIAaARA6gSjWjtduaKUat34AdOuWbXZwRu7OjDmazvtYlCiVzHkfwbASOLgUUSAu-ExrdiTRmsPYDwd_ayuOhwsc2mztuSlw08bXKMEKn2-i9z1sdPyOtCV-Ood9nuDeaaiJ6W3i4U4KfFpTwTECFQg_qZjdF7vubxwRMgLdTD05JVn-m0YpRguJ7mueq6O-HvWJxzwqiLq7BEHTzIz5wIwwO0xtSA51zekK1b0jjilTEhiwoEbb6-vQO2tleltu24XLRFpVJrUf_ZobXWeYdDpy8n2fT7YYc2Ttj3Rj3mibeyrfo9VglsCq_L-crUWcjzmDCxUPa-aPnehHk0XMIQNHBgkVZNl_0geCwqYxjZWNpkPHZEQqFHAuzSv2pEH8EVNn_IgwTMeWoKeQfbGL3-pxFXKkWGQaAtw4zFr0-GLcIXqLi-uzXop3eflNLTLqBfe0NHFZtmlGo9lQzILmRBP4S2zAfVc88us1p3I3qlcITZRJRBRqcv1G_bQ_S6I8x-643nxG2zOPVemDqMQnQW0P69s_4nA3tJ-HucFoPujwa00kt2lLt5hikZdpQVaOXNtJ2FaZKtcCOlHmJF7yn8XvQ_u1oTmArNqgZdSb36WI7002rnHbgQrzqbqUWauwgf_IHDB-5FSan-IvydsEuyE1pDxI7E7J6yZPQ2H9f9hl5ZK21vXWM2k2rxHuDKr_ZKf3QE0eICMborao5JDRpOGesB4JcP0HomFTUXUYpNOjYK1UraUCgy8rgwGbas4tjTLK5Wcp4_dxINP5GoLxXdHgsvNHjoG0c-g6kclJ4Am1-U_oNtcyPjx_Q8dr-cXZ6BIKRUASk-uMOHQcKbRDo18PEdFVRCcrNkVXqvob5gKdjWZEH0XNJs8s98Jfh7XNbx8Qf2O24-NLL2ZMcKffHFyu3ufYNHvUAISbhYZMV2Ep6Oi4uJSm9rotpWl4voiyyW90GtZzvTmnNsDiq-4lqDeGNEtTI60rFVX0YLfSzPHTqH7M87Xeqaepvtl_R2Wgeru-Zhcu5cO0AQBTqU6B3WbVn49wbKyegx5Qr9RIgtfM47BrwLouyowfIDqX0MZXkNGfPlEkuZRX56wHtbfD31bFPuKy8uZrgXrCXmhGSCADrs31TUeokopZCNs5LmF3x6jFEYWaekYGxTeloW6gLkvCsalO4r-HA4xF6BBMwrykpQesuyaDfVZ6Y-HR1dAPagqFtglzc84kH6-zhzrHrBZwqpptKHLEqzdQdkF6_Wct2xo3537nXLyRTYAr5bYzF4fiWrxNESWbKb2qkjjVolBy8SVy441tN1ESDisE1VJmHv1GCk9chhh-1cznoDaCTe23cUXMvRRlTS58CzIu3dN4BKQ3A5pe6e1Q1r4QBwIbtrnbvWkEqfnE9NBMYQBR_Ln3QyQQWEpDwO4h3cRX56EroQGYZvodX_2tuzIFSfNHArhwRPfeK_pgty8ZmwHlplAM3sqZKAsJEzI-LO2hwj_1ofmFoIdrxawPo1tX2zGZE568SIc9l_6z8FmthV03l9qOBii-QirqfcsvPiZO0bwG2FMwcg3aKeusuxF41EaK6KSzyCCwNS4hDQVM2DEbXW8amZv_hX9guHESi2WeIoR-lcPOvaFJa5eazuZE4w7S-0Lu9wHCM5L5bAPrstzJowxZmZRG4bZSWQSyHlWl0trSJso-ye2bdFabXIYxPC0ri4XHxKHGbG2gXTJP6P9I1p2PX5iigAq-zY0wxnZ3-IBtgM9irPGOfy3y26d5L2ZwtALQat8s-ycc_WbwouODBv9KCNctlfupQcxKTFLB5YdcOZCQrxUAM5Ebt5MTRKlWRzYw79CvGxLIVxWZ_fkmfhHNC353tYlqB9kxi0zOEWs8x06wJt0ZxmSCKgqLXA7H0lqkS0dhdQ0r2J6JNWtga3iHUDpbFhRDr_4LVt3dj8_XlfodKxDVUojL_Zenlz6YE6C9VvePfVahHjNrlh411xfSlBadamb8jf620RfrD3NSd13UJiqpTEhEbF4_EGA7qJnvN3a9qydWaZBUP4HIbcLUPW5p8LpB9-yJA5d44XvpqbpAKUwwwpKxAbjmPxx39zcV54g_1L4YCkjg1JRJjNXb1K5ioyudBFlz8dpXUuHNK3XMVEp9gxs_9bZUcbkYFWcJpsFRpQx2IWn0FZ8KyBHV_oxLmktaV0i9nYXtgZ76fYPz1JEvRzT5PybEfYUE5clwkRTdHZxa2C3cMnaZowzlXaDpFF38qzDJNf-Irpu1VDXqDJ2zlP846XcMEeKIZET4pmYNUQbMSpett0DNJnCrue8KRaWhJshyXO-Bu3i8X7-eBmdGKYf20jtqVpJ6VPBcQuZXg4aH84uipOy_TFSesmbYSJsGL6QbPbYhkRky_Pl5sGJ_gO9JmpQ_CPIudYXO3LFcugOeKFgGL-0h7JKVJVz-wygXlEvYmE5m5cQO-VwJKvlD5IS9-jW22LVL0L5hDpZPF99Kk_cz59Rwbr-u6q8roLJiR4qKU1aWMZPsg3_vs74G-0TW-SWQcPN6i04pLz2vBMThyhivU7lSBuZ-klbRKceu9MQ09IQDQR9_QITEcQtg3rncaiaKfymUGxv9nNT0DyPFIKxCcAGOjjzM_jFYhh0qFPJTfS8H8zvOXBrQdx8zGq23rCZ4A_XJ3PMgsQhbp8Hc2IsiEzJnHkJLykp18mbsD7f9glUaTc9o2Pez7ZvhKgf0xLXw5EWBqgaSRJIUBGGm31udBhs9e5gvGDa7JJ3Mq8PqjUp5Tgjz3vhGIe-LVSGjDQ5q8EZDPWm9Nt52D-6RWdpUGlOoK0LGBRaSBvGVBYMtrULOW5-VzJDmDjYpFvONLxjmCJfUa3HYoPmQf30p0HOMMv5vAYdPtX7FjyU1I1WIAVx4DnCfQu2ib92Z5Ko2jz3JBlDdNkPuNnrVmTquistGdyhVWYQg0MR1UXskYEZy9oAWmuNl8tVZoqENUK_C-odOWXOE1HTeVEhAKy-Jwpk4nsC08geWkKc2dNtdvYnxoS5e9qNIKc3ONt7ftWBTm36fCUQzgZHzf4OgT4flYfwmi794gc-2Ulnq79c3dwPsO42R7iIB975JAA_DLDhzKGLZzYa76sLxReWV1i5kmCh_qkmUUYwoCf0x-lwOrLw42HymSltQs8fYqNHLUnxm8dS9iR0DAiPYOtCX7G7W1XIY83Jul5nLNPZjb3oPK61RhsT4K2ot0ozs77sDUDIgXp0hvWoJtsVeoTjrrRuJPoV9Mc6mmfOwgiUK_Ql6ZtSLQQ58HdeHViQ4BT6_o64HziRGmPBI2G-Qzvfclsau5m1xzJrrE8PsXAOGGFW56YOMfv02iont5_R8Z2TQuuwv_XfabWEYiCxVAPd-1hcrUXqdKjSaqHCr2HX0TuRGDyCzN6XR3z6uTYbfwNmxMetHvNkpESV6F76dc9zbMi--kW0GZAVU-gMn9mVlVeYnaYAizDwF4-Hvsqa0e0k8ZNE6cHJ3u1-mkVkDtefF7-nMO9-_pL4wIRfmWfy5_0epIL10v6HbeuKWeTCk5OShXkv--I-gQNAvhRv06jwMk_QddttYTts0vd5wTNat_CylbYgKMALNKVqGFeQLCk84EmqBbavvP0DBA00PWX3kSsH-AWD3i_si5Cclv3QAuUi7tDlz267PaBAKwHd6O47p0Uzvnk7WGP-h87uR2TNEpDuY9pc9SybjIwUa0-i0I34EUk7rt8UD9fDEDNAUS5MbV5dlfzHJpO_b6l8cPfeCLqhHO99rOwmxZugzIt8GgLvJSnBatYnCajl6vQNyJ7ISb5u70duqEXAMDA2xPv2adcqWo-IApE1QeAWQ6MTL4jDtNgNVXOxMEkDIE_xa5BdE9T4viuN_pk7YQtixkMtNtf76ES1WzQfu3gsYU8M6XWn1oqgjLl95eJOek-JDTzsUOPjXC6uL1eG2V72VzG3lfFxVzoU10ssFnDZLKyvHFq2cC2koQFGJJncUScEieMNIb8y015jUUoHk-IkxvsRdaWEAQl8sJN_jjzEf6_uDghKyidCuWzwtIpgYcoudXFBqg3OqSFWE63UXNeURzm3afYv7BIOTj-laSU-M1Qi1M_cwoH3mntobHDhd2jhdPEYjITge-as9JcZS39LvG-TXZXzn4ohdzgzZVGZ9EpEZjdGPR_1SGYAwQkrh5cTLFIm2MxF5E96vdO56lqAwegMe8dMNCkESE2UMsgsYnsv4IcWXb1vuCxbkF2pfom4JNm3ZA7C9L_VVP6stKZMlFzwauUjLZaTdz7Mugq8RSf77j3jqPavSfy2NtwFY6jh0C3E_lP2yVFBtGyJDXn0-uNdZNzdUnrIetfoDGGeciNyEQORCA3ZxQ8LcLa3y9AP78yIEVYW_WTkViw2QQKpWoy9Cl6ewklUWH_Bd2Pk2tIoSHKYhpnBf-zTNEw4ehAEHClXCaqw3dD0X_alvcJ00JKulfaKDH4ig_OJf88RIUtG4XL2sJfCzxKZ4UcRif4-4O8z_eqgy_D2twGlfUc0GgBX6Qjkxnhu5HBpe-sVMobkXetFKU4xruy6lK5qtwjuNhHNDKDMZDatC1HjC1QS89vr8rYiqDix09u2RFrG_wmGxwydcplxtQ1zos9BxAncrdGYry9bhQcZMGd6jk69UU7ryLy0TytoSUNqsM9sgmBGilBCTWtN7DaGlPgjTyiLi00Z6sHWOfpwAwOYCdU1b8QMuhk3qwtehF0F-4cUNGqaoobCp72x4T2bEevKWQTw-wKjWkWd029D3V1cwqhLWrcQQCYzLTscY7iWDtqhUjWaLtvurEWkFBw16Ro15i6eApilmtYq7PmjwNYjuR0Pta6vNXPZ86doTeqaXj5ejgsiv7srRBWsyeSSLdMhrtSvybEX__RMLOpCTmOURghvslzVOLNDhtvNJDO9-0w4h8Mj7KkOz_vkEJ6V9FV4VaD0uNF_yn9gA1AIxd8Vr2mXH5tXe5wNlwvteN9wTIv9rMBiRO_dtuTbB6z_jtCZ-rMBqux3vmTI3g-TWXQdSrFuPALSkYMRFF5Vu57Oq9ZAmPAB4ydJZjUMRiwRwddV3Okq031F2OfMh4ozpkLoG7IxBvOKFQhBrdqG1PtCBX3dtm2QjVqkt08CULGyivmiok4uMfAnJ7Ff3_O-0C2M8gKHIOwiRdxnwccnd9-U0ALDdFGTHd9ZChaPMX4nirPLWrxxZ1qktgjLSQt3AMyzLS8ga2JVDbApZGzzsANn9-uaa7pul6ukkQ_ZCab1uSKf6rUoWcUHfDSLhRWFqBqyCg4DDi3Dx_8ymjcIMAiGfZ1p7eM-SvKPGc6pb_9leWxUlN8QfO7FkKGLdqUCI138mHet-rphghp3ovUbuvr6qqv-xKC7SrPKYQELUvwsy8y-qo5VWdb9_LPHutkRXugb494WGeU_4nSoMC0NOPebXRJIGaYDvmO4YjVQYu4ilXm1hwKTC693NB9DhYbATjDJ_7SeexrHdK23HcbkULMhDpR7eoEkxYsv2lmH_CPrXxlIFw6twjlF0wWQFNzRvcNeIEFw3HHYACfJDe_GjIv_4qbAYSWhfRPmMFRAluXJOSDT5Ulzll4h154-VmOeSzJhmpE1pH4EwhNTRaPveo1W7eU-nUByBUizs_qmMQcRyPNycjPpgyiu9vCedlZ0DNFrDB-5dMQEklmre4t6zjrAH4HRyEtVGK9X9rlibTsKquEsg7Qnwi8YKyT-n-VTsivc_Xd80GZtOcDvaDv5gUCTybElNWpkHIk_JDyTcBu-Aoaoc-4uXvZ8Ug5PX-nHwapJp7qyz5EEZo0r16e3_0MhIjQSbT-foOMf43g33-TY2gLI8Q-Im-6W9K7dGzxJpUCkp3k3_zQOKlgqHO8YW2R4GSh0sdb_v8avLVd8J_LdM6FjkTsPr3Mv03cEBz8AhJpTxZVTT2nBklPciCqaPp4h55V2QuIQzIOrFgbjh2E6hY0AqQnGAnkhQCbuDT2gIALngXkz5kco0SwA6PwISanSI6_DvAe7VqKUjsi_PQWHzF-kbNUx2YoxI_Q5uQ3QClCb107mWVaqvx1QGn1Z5DRKiqsegVq0BFEEagdHDZX0XLCc1qQv4yVe9QirOb6D9z4mAdd9f60Bz-qGPxYKr06Kc35c7WlVzaxekL3j8JHH4JVASkp-wBN3SWV4VWgscFO_UTJH4MWQS5LuyQyu9d4rSHpHjY-0CP7bNZfC-wigZ_1-88ohaVGFczWWKVwHizR3mdLGgwEXbr18zk_QWTSX1yBWPs6qgN1gY8iT0DWTJ0EdV63Si-IpPcgsuUaqI3eV3JkfRrcLUBUAAIwpxEjbGqlsIEucAqe5Hezx2sQaVJpttsM-mQxJMQqOeyc2dY4KN9nwzx_p6fgnD2fFmSFYAs473YbVNYb1UgJnmImZ65F_xSB-SYmdFr91mue47aA_U1xZVHy8fq-j9FPK0Fov-PIywBbN74Z-5CHq5_p8hIq_f-lTfkVV7vWoIuvpDhZ4xxXySCEKBQVwV4-dHtIXXzauMYtzf9-rw1qgEbl2nC-fcmk1g91u3Ks_KFE2LpLyNXJZMouekZLn3UmIQKERXMlaeK6bHz2Dx7ho-Wq8UO5-4F0p6fI-RPAzZDOVlHMySA9u_9wQWJ2l3TDvB9F4IjYj3LI1s70rEh0OQamlYrT83a7aWarIVJd9CxecMymovuFkzmFco26HQ8AV9L4uBGBEKHf-CgRZ-fOnzVU1NzoyExMDB0FezA4adzYgYjIvTgwrurWw5JalEg7KOoToY1md2Tp2YXUQiVb6_AWmjBDcDCmkHFIH9WPkqdiJlAH486aPbHX083MoCyU45qR5TTQ2cJPSIyJokx1AvXPMA_5P-du1hscYyCZbtLLR-mPvOteTXCos2vyh6NWAQJ0-Oo7NMdcvwQ_6UJYZggTgDvgfl_nPBjCixDphOaESlgR_oKrJmvVIZG5h-lxHp39KebD6xGXiyFfyjVBXS0ewv35EOTGyO-c4HEShcdkDIDgvhGaKRwPSkkU56sp3YYnCLU7kit7mDGL30JP0XDUzYlCrraqgxIXSypUs1kcv6k2pG2HKMmsyIcXhPhQkEpN7lWNnKAnqrMmCO_IUFYiEuTtReV7SgtVxk0QyVznGm5CX2wyvfmwC5zTMEE_7LjFYrQB570Jag_wBemOvgqrMplfmzDP8wNKOwd604gp3zSQCXX0jXrvXdTgR3oFI25L-BvsUsuhyCnDb8lnp2FEB3xYNAwYZ8S7NxON644HqELAluizOX-lkbSPd7Wp5FyHEsTy8LjB6FwQprQLTWuub4-9XdE1mRVzBcmqpB1XNRRezqs0ZRmTXbxYGKLfxr_h_zGWIfaBqqgVZYisdIAT0vaZj7VBv3vxoiMyRkGthD2hpGzpZG1qlZzMC5Df278mRw1oW0xVagwmHcTTuBwcKaVJf-EamB8at8mtlox0Trx_w2PjtIKafN7QI_OTiEyMMZ2TduhY-ygYkp9zSCkrIyse9UcL3Uj8Uy7whkDk1juY9VNCkyJF4IBj-1aErK8LVvC23gy6ze5jnvBLHoEyBwIxAITyRSOUvBFVKg_sVe2vcakLAQ3J5shLpOQ3nKT3ZBVRowvBc2pkYUyZps8I2D5jK2gQ4vSxgXLRdQynOmUgXOBV4dszcIXAN5cY0I1WhKm2rAhwK4KVXv5wcP3-lp6beUevL9tLQot7o8bB1Lnq51RpRuBH48n1bq_IT5-HB06SgGu_-VDxR_eY9zfDQAiKb9K6JVR4WKX0a9W3UvLGtOW5LulkOW2VeZdbht6rg_paVeXLn99K_w1PMfiizsdegLRYd5fAOuiyqA259w-PRx2m4Z70zNYCjsWoHl58-QCWp4FOyf4RQOEO0J-Rvpf69REHTUfMX3JiS-C94MS8ncRjI2cesazw-mZIokbPcDcBg5KSxkXk-xpAxmFFY5F0td701HTf5qpBVYs09ZvHQLiHvoiEseQi7fZCSe6h80_L4XfWTK-zbHeuxHUIGYvvlyV_uAZBiD9pC5M2SMfc8wziSYX3RoDPEEKrgA0ufcZUaCX1FU7intwU85K_gQ_Rt89L_z86rlxm6xTcUDnZAWdYoIfO8TKDi6StuDyq4sJas0AY_VPPj-1odMBgB0ShjQVfl3TTxly8PTuZsVwqpl5kMH96gU0lpQJ3ShP-IQHlUu8h383LFnFccL2C84i62GOL0h6Z-YEkHxsoVogpPDuK2X9YDZcxOQKcEi6HEL6aDPTeEFzmqAYNe8AUWSopjxOYPEKvtNAsgqXkAaw8zXXLem_bvnJ8TSbPRlGeSkCNqM8s2fW-NGZX43znbQIzgpeDwftQHnjajRiteveybczgNVcsJ27lSA-1Jh8Tf0XEcfgipMXhIX-Stfnpm47jsDEuLx_qQByN9Df_p6sE93r_M25ZtZzyXtHVut-8zkSdBm72E-CzFwA_RGm2iXR_F1UWQnpMVaKm-eLW7kq4jOdaUDbYk7V2KK-PACYL07UtaxzQZwEh7vpfciaGBcIw-ykCYJxwtJtZth5aTblz1ZS1Xwd6PsGJYg_C68dXvSudcExOrx7mDJEY41ZgsTjCYr5M7mXjK5F_EKX11pEMTtlQCIdD_uo7Z8TTqS3F-XlkHQGGgyMkBVZSONM_tFCB44ttl6ZX_gx8Cl8U92uwuq41gbVYULGWTTvn3YrB1zABRwpBIg3nh54QC0eUVkThB-sxNKKitGZF8SLSIDbl15Doi7vhCFaOIZ2hqN2LEt8Yaf6g1xJme92k8GeWqhLL1PlH_D-6tBcEMxJgGiIUtaX3YPgjWIRBivq-l8D0GmYjb7HaNUzX_iYSvieaR2fvHR0d00sjWq5tCr_-3p9PL3-cwttrQXXykrUmDh99FFN3VJDPrKeol9kpK5n-lhutOvpkcYemyHzlnjRkJ00kjaL9CGbQ2WVjAqsVKoEg6R0vZblAXqfIdgdkwK5V5FiXczRAjz8KJAW1crmpDCM7DpMdrzcrJ_FkgANTAsD7fpZxJ1QRLHKbd2NsbDHm1jnudcBAI573e2J5A5wNACwD8Av-99lBfpa2MXcpTTcPc1u0a818IIENaFNTbIQZEtXtuztGZGML2TMcFJym9Dbcj_dESjsBRFZQCypJBDE39luyesD9UKGlyYib9EaEnru2H8TrSqJ3q2af8iFsxt1bPWq8GHOLFmF-DmA9OqcE70D_VJf6UaymeqspCUW3-v_HOG-YNAYxbYmuO1I8fLduH23IsGywM9tlknTuOa8Sv8M4kQVONWwroJbuVyaoh19eebFaEQJWhjcgI8W9vEoVbEYpfSY0aCq5Dfght6Dt_sJUWodYK2oVel3eIzIjXcPUT1a98LYK7lZ0tGvArfk0rt1SHljQgANDSV4mg0u0wTU8EN9jL6qNFH0wD3LEk-gjh59mB88E4WiPWslRetwb1FMWiP87elABC7yXeqQn0jxt7FrFrb_cj4zUZrAowiNGfqmjj28QYR1UQxNjC77ckPhhs6IHvP-Hlujw-By_AccAl7nOhvXyzZg68dKc8hdHfRhVVEGbsPd3rLzeOdEIgW23X9wVKidd1QpywoSvAEQBZYb8kmR0iV-XxhZGtQimxN-ql0CwPEbwTEod8eeg35sTn0R4H3gFeFLzVdyFDi-hPDKB15m7sGijW2rlDMJjyqFy3M6TXPn7SrELUJDVBTZvTpXdptGHzpLOjxwQtIHQFwQLP6ISR3gFEJyJi02h_P-eOYCgvSqilfGcsVlQB9czySJmYAhfow5dRKpz4__3GnxQnKxmyAPflypcRwxvbUgNdQQCkv5De71TbOU0FO4C-4l-jMZI-k4u9Zzn4-kSd5fToV_vEEtMMirWQv8Y7GFnY1In8NXZBAL_mqpUedUBgBTWLqFAIIt5phk3xqjytmMbQzb3ERbkDYxYZATZKuM3o7CsCfZ1EvLY-dde_oS_8qmZ_sq-Qr97S_ow_xBi2iumJ2zZwaZIqnbytK1SuDesIXHpLgLRTHOESmaayyLSNtm06iWwG0LA1PlRNBNhTtxhcNiQu6kWXQbIZJ9xFlgoGmWElPY3YPgj7T94Eqwj-eDDnJS4qhaYBpZ7Xvsx9GWU4QDaz74lw_OBUccAqJxiuCzAFaCftfe81s2in6eGE4aIyAPRaEikF3zplfglurYAc57Kp4M1G8eU-0LswRfSaBaljwHa0VJv5aU1Kng-7F2UGhnUADwYhpf_G6rl9bCX_NL7c5L2QVulUq0GGjfXbIx3tHh8YS2v7NpRdfPfJ3xA0_gF-r9FIf2-Zdk8swOY8BGqiWesFfioMlXbEin2acuW1qL7W8CYJCdD2iXF0vRpTcoOGRXJ8TZEQikOFpxR1xzp9WxZVfIeQfHgQUEP1gT-BPkezSjwaBOPWVsuEeUvSgO8qhXSCJNzMMBfYPHn9QHbrDQl-PBPZhLONyQTUCso80NafTEjTj5xRFoB4aPcSigVUgGose-MyxB3uyS8AcnmLDNbiOn7qkhW_R5TOMZkivTJ71yso9nM-iU-1F2DXFc4NzH5dSQZsHSLXOtZVhOQ95Zr4UsUH6BEb6HWJlYQUJFzS0UBdoI_i-ywiEGFSURwqy_yZMmZ6CFelt8nI1uCEiM5w10YXGlNL3nuyZkLOcObX7DxHn9oAkdrSgcQUyVImKlDrBxMH7lyTcPqVCsuBkGiH7DLQIglWdlks4WjuxoACQr4RMe0qRrn5Ap1Nj0iZ6aOaYCfMKjoq3ASRS9p2NaTSlDzuimU9YM9DDOy6kmetjSZRTyVhktZHXSggi0eVZmYKxh7y8XauQ2xnx1bFASe3JRNl1SvGXj1D2lMJWGTxHUdDvAToy4TZRD_WxlvKpIQ5se39qHU9eOMk3hkbkGqwXkEk4RsbF--r_ZinnfUILMRAtRmk-vVOy8-4TA6xjtiwIWTwQIYat3R6uUJdz3iT3tlh5XcZhzO7h0MzxCKlnj9mxGEtzFmWMgMU9ZwpmztLKnNX-QSxrUMN2tofZcBto3-7JBrbVeowRTViHTdp5WGydz0PigPQ_8Fcy-UG8nielqj-MXZLfpx8Pjebq7q7o36AcnYtpp05beMLXDq7QTc16Yw1P5dhg91jCY4963kxD-x9lktXb0r959q2x-sWu6dRdx8HOJRbku2dhkXe7GPvdA_CNcN4a1PG6YskatqcrLNwsdT025l1ATqqk693Y5bO6W3fhX9c6BGsOTuctgbi7Sz7W_8BNDaCy4qh0IJtz3Zw3y64VntFc7s38iGFgBVsGYTmYR_OBTdc9T1IGt2hGfvbQfm79UcfZMKEjC1wmPfhfsRTkMc3P9TyEHEqFwXlj_jWjUC2Qi85PVapzKaHlW9PbiGfinIYmTVNsKv5hdjnzNbxQNOM4LKRGv3djl_w2Kaf1mxbSyHlS-pJZzhDAJMcfAf8aDpGIXStJKD3IKOYGx6Ty1nutF_zBfGVqkJfNDBwgDpieY7HgpXefGJP8_4MkvMcIQmM05zDg3MuZPIKghOV-Mvu7E2ZHz5QwNrHWIdeHeJRNlaM2celqa9TpYanz-aj2JtVtqmk4V2hHnZ9DsAoi85b9DTLQv1RIfJOV8n8ZkmSYdJorT3oZ6o7HcNk7g5TJXbxjLJLUKHRB7KHxll-vWfOaHVYRcwDd3_00oPk9_1oobqHdDTn5dAOAzMrox3A2oZboTpX5wlcFQlxLFniqc3-yWoXDBLdxU4Lw4zuWb4ehx2yJN4ssClfRxTleGNbXxfWUREtT4qxAcxrZiS_xVJcU6EGVjumu8z8e-516QeLlJyqpdjSordZDJuhKGDOI9EHThA0fhCPTOeSQ7p8vyUhbj55un7bawA1ti_Qzru53HpEDEOPT4qZzWHRT9dzD4iXFrFdZ6xh5B43tZ5ozzzLbHz-7TsDaAoxTig1Xqe1Tfu3nyHaCXvDwfsE7PLgdh4qB90ZO7yyciYFqY7moNtZ98MkHiAmDsCIGK0KxXoddCHJkebfGKx6X5yS4TiygbGUaYgG8UIjnIDhYIY-phEI4-5V5RhnuiFhViufpgEzKivE1sE7ADufGqPKMfLJ7ppAI6x4rxzyA0MDZi7bn6ATu6GKcrQzBYNhpTrZPmRADXH65WNBVn0YEYKu8h2uTVBO3RoPvRk1kFLZ40fqssrdiM2i6OBI-AiftJGFt_PdSy3SC8LOaqvpfY=",
        },
        {
            "id": "msg_0ef7132e6d030ce6006a14645790d0819aa7621eb85209ffbf",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": '{\n  "block_id": "T3",\n  "task": "transfer_search",\n  "from": "Ninh Binh",\n  "to": "Ha Long Bay",\n  "date": "2026-09-23",\n  "candidates": [\n    {\n      "rank": 1,\n      "vehicle_type": "7-seat",\n      "seats": 7,\n      "price_usd": null,\n      "price_vnd": 1989900,\n      "base_cost_vnd": 1450000,\n      "overnight_allowance_vnd": 0,\n      "tolls_cost_vnd": 359000,\n      "surcharges_vnd": 0,\n      "vat_vnd": 180900,\n      "duration_hours": null,\n      "distance_km": 250,\n      "applied_distance_km": 250,\n      "applied_overnight_nights": 0,\n      "includes_toll": true,\n      "meet_greet_included": false,\n      "source_url": "",\n      "retrieved_date": "2026-05-25",\n      "notes": "Private one-way transfer for 4 pax (2 adults, 2 children) in a 7-seat vehicle. Assumes normal-season pricing, no waiting time, no sightseeing detours, and no overnight driver allowance. Route distance estimated at ~250 km. Tolls are estimated by apportioning the published one-way-equivalent toll packs for the closest relevant highway legs (Ninh Binh↔Hanoi and Hanoi↔Ha Long); if the operator uses a different highway mix, tolls may vary slightly."\n    }\n  ],\n  "search_confidence": "medium",\n  "search_note": "Used the published 7-seat rate of 5,800 VND/km  and the highway toll references for Hanoi↔Ninh Binh (208,000 VND round trip) and Hanoi↔Ha Long (510,000 VND round trip) to estimate a one-way Ninh Binh→Ha Long Bay transfer by splitting the relevant leg packs proportionally . The general pricing formula applies VAT at 10% after base cost, overnight allowance, tolls, and surcharges . Overnight allowance was not applied because this is a same-day transfer; the overnight rule is only for multi-day out-of-province service . Distance is estimated at about 250 km, with no billing minimum applied because this is a point-to-point transfer rather than a multi-day tour."\n}',
                }
            ],
        }, # type: ignore
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "transportation_cost_estimate",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "block_id": {
                        "type": "string",
                        "description": "Unique identifier for this query/quote (can be any non-empty string).",
                        "minLength": 1,
                    },
                    "task": {
                        "type": "string",
                        "description": "Type of transportation-related task",
                        "enum": ["transfer_search"],
                    },
                    "from": {
                        "type": "string",
                        "description": "Origin city or location (e.g., 'Hanoi')",
                        "minLength": 1,
                    },
                    "to": {
                        "type": "string",
                        "description": "Destination city or location (e.g., 'Halong Bay')",
                        "minLength": 1,
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of travel (YYYY-MM-DD)",
                        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
                    },
                    "candidates": {
                        "type": "array",
                        "description": "Candidate cost breakdowns for different vehicle types or options",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rank": {
                                    "type": "integer",
                                    "description": "Suggestion order, 1 is the most recommended",
                                    "minimum": 1,
                                },
                                "vehicle_type": {
                                    "type": "string",
                                    "description": "Vehicle classification (e.g., '16-seat', '29-seat', 'SUV')",
                                    "minLength": 1,
                                },
                                "seats": {
                                    "type": "integer",
                                    "description": "Official seat count",
                                    "minimum": 1,
                                },
                                "price_usd": {
                                    "type": ["number", "null"],
                                    "description": "Total cost in USD, null if not available",
                                },
                                "price_vnd": {
                                    "type": "integer",
                                    "description": "Total cost VND, VAT included",
                                    "minimum": 0,
                                },
                                "base_cost_vnd": {
                                    "type": "integer",
                                    "description": "Total base run cost in VND (excluding all surcharges/toll/VAT)",
                                    "minimum": 0,
                                },
                                "overnight_allowance_vnd": {
                                    "type": "integer",
                                    "description": "Total overnight driver lodging/allowance cost in VND",
                                    "minimum": 0,
                                },
                                "tolls_cost_vnd": {
                                    "type": "integer",
                                    "description": "Total tolls/road fees in VND",
                                    "minimum": 0,
                                },
                                "surcharges_vnd": {
                                    "type": "integer",
                                    "description": "Extra compulsory surcharges (e.g., Tet, peak, admin fees). 0 if none.",
                                    "minimum": 0,
                                },
                                "vat_vnd": {
                                    "type": "integer",
                                    "description": "VAT amount in VND (usually 10% of subtotal)",
                                    "minimum": 0,
                                },
                                "duration_hours": {
                                    "type": ["integer", "null"],
                                    "description": "Estimated driving hours for the itinerary, or null if not available",
                                    "minimum": 0,
                                },
                                "distance_km": {
                                    "type": "integer",
                                    "description": "Actual (non-normalized) planned route + local run total (km)",
                                    "minimum": 0,
                                },
                                "applied_distance_km": {
                                    "type": "integer",
                                    "description": "Regulatory or charged distance used for calculation (km)",
                                    "minimum": 0,
                                },
                                "applied_overnight_nights": {
                                    "type": "integer",
                                    "description": "Nights of overnight charge actually applied",
                                    "minimum": 0,
                                },
                                "includes_toll": {
                                    "type": "boolean",
                                    "description": "True if tolls are included in the quoted price",
                                },
                                "meet_greet_included": {
                                    "type": "boolean",
                                    "description": "True if airport/station meet & greet is included",
                                },
                                "source_url": {
                                    "type": "string",
                                    "description": "Source website or reference if applicable (or empty if unavailable)",
                                },
                                "retrieved_date": {
                                    "type": "string",
                                    "description": "Quote lookup or retrieval date (YYYY-MM-DD)",
                                    "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Additional important remarks and policies",
                                    "minLength": 1,
                                },
                            },
                            "required": [
                                "rank",
                                "vehicle_type",
                                "seats",
                                "price_usd",
                                "price_vnd",
                                "base_cost_vnd",
                                "overnight_allowance_vnd",
                                "tolls_cost_vnd",
                                "surcharges_vnd",
                                "vat_vnd",
                                "duration_hours",
                                "distance_km",
                                "applied_distance_km",
                                "applied_overnight_nights",
                                "includes_toll",
                                "meet_greet_included",
                                "source_url",
                                "retrieved_date",
                                "notes",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "search_confidence": {
                        "type": "string",
                        "description": "One of: 'high', 'medium', or 'low' (how reliable/robust the price calculation is)",
                        "enum": ["high", "medium", "low"],
                    },
                    "search_note": {
                        "type": "string",
                        "description": "Narrative note about the logic & assumptions used for estimation",
                        "minLength": 1,
                    },
                },
                "required": [
                    "block_id",
                    "task",
                    "from",
                    "to",
                    "date",
                    "candidates",
                    "search_confidence",
                    "search_note",
                ],
                "additionalProperties": False,
            },
        },
        "verbosity": "medium",
    },
    reasoning={"summary": "auto"},
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": ["vs_6a145ebdf1708191aeb15814e40479e5"],
        }
    ],
    store=True,
    include=["reasoning.encrypted_content", "web_search_call.action.sources"],
)

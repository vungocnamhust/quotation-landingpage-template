from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    prompt={
        "id": "{replace here}",
        "version": "4",
    },
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": '{\n"block_id": "A2",\n"task": "activity_search",\n"area": "Ninh Binh",\n"date": "2026-09-22",\n"activities": [\n"Hoa Lu visit",\n"Mua Cave viewpoint experience",\n"Trang An boat ride"\n],\n"pax": {\n"adults": 2,\n"children": 2\n},\n"halal_required": true,\n"special_requirements": [\n"family-friendly"\n],\n"search_query": "Ninh Binh scenic tour family halal price"\n},',
                }
            ],
        },
        {
            "type": "reasoning",
            "id": "rs_0afa1eadf9c68e50006a1431533e88819a8a8501aace3fc978",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "**Searching for tours and fees**\n\nI need to limit my searches to a maximum of two. The objective is to find tours and their entrance fees, so I will go ahead and search the web. The output should come in JSON format only. I want to ensure that I gather all the necessary information efficiently, which is crucial for providing accurate details to the user. Let’s see what I can find!",
                }
            ],
            "encrypted_content": "gAAAAABqFDFzOfXKv3TJeHTdYo6VHLryAGPYV1kp05a1lNWDEIENuEBvljB37UKkBaLPWDiAQnZWgnkClbtyCQBZqmJZTZmGnp2IOZac-i05bThKqj5bmYliAYokTzrmaEHtJa5asWCVvdImrbvHzbT5h4rXj-T5UBn0TyxuGYnOdco_zhZUE2rhvUj1ABMZxKdhk7pWHonOpcllsKzy1oLVx_uA2geWp9tGeaeO351BiaFeuPE9VCZxTc_EGV_5wtDV9cMxaK8gwLpdl8JN5DPZxUUXtsh-TVfGR3Iv816yLB47C8LaHbrhNz2w6UOg7ZNXM-aN46k-oKd7jXXa27WhihZdEJHLkCMgvADUh-kusVKgXWvmF2I7YAAuizrnMJNatb3h28nlR70vs1ZCLYbV51zh8wvJZXOa_9jX3JDfIyH_1LJpX1Cz6I7k3rNqyd1SjLFV4C0--St-5Tlxkj9DPzGVrJaol8Ih9IiiE4FAKNUdrS97pmpBAwJXWSlZlnPvtr7Xa_U1rNvzz2wot2mrhhHR2A9b-oRdSlKsrYYfvjrNtzxq_z0aTluVj8t9-KVKB04nc5booSUF2wg4TaHbhr8mDmy3AxlxBUsqbxdNhhcjLtdLi34euTghwRnnHABBpwPYwPjd2zP8CnOBvIvGo-ZRbWYovb3ax8974ojB4MYxJHjHljo4WTO_VloRxqQylEDI_DB9YmsuSSAesU4J_nUP_Dx6qthdlDj6iMgpnnka106uFBdFnQKVOZoCd730PMEBfbs-J28tzTiyJ6yJXAmUjwzDaMuyZ56r_-2TgpbtqUWxfRWfQ7-PNkZ0LMQi1kH0R3KawUeBjJPs9Rh0mogVLGiyj5G-o5y7qCcnBDF1HuXFvE8TI8-BmsRaoarq28_YTlkrCTUlWRQ4gzz6obh_w2C8D-sMe3g0yQdYIUMVXioHxwx8GAJlqFzFZ4Lqnj0crkPphVgCwd_gocr1ScpBMFzFg9yzianHPuwc-i8qVhGuFyHIrM0e-wPkc-9RzM6cwC302N_IUFljBV2sgYpVoL1Sc9ocXuKwsTLMCexjcrichVnTc_CMUfIZ7yEmvriNOtyx4SQpoodd89rrfmpLJfnJMw==",
        },
        {
            "id": "ws_0afa1eadf9c68e50006a143154f060819aab3c295f0a5824c9",
            "type": "web_search_call",
            "status": "completed",
            "action": {
                "type": "search",
                "queries": [
                    "Ninh Binh scenic tour family halal price Hoa Lu Trang An Mua Cave halal lunch included",
                    "Hoa Lu Trang An Mua Cave tour halal lunch family-friendly price Ninh Binh",
                ],
            },
        },
        {
            "type": "reasoning",
            "id": "rs_0afa1eadf9c68e50006a143164c324819a87d9ac96fa320f0c",
            "summary": [],
            "encrypted_content": "gAAAAABqFDFzcUdnPqLyJMNRkBMtxpCyRlrP08hCnA8fIx-f-g5_6XOd93h8G35ZoqbfY4CODrAV9LWSdtNdeEdE_b4ZjgsbWAprTsR_TIjRmxrn_kUImmlCxsxfQKpvliGXj1RSJzMQgLOoRH5wnAh7eoUttrShnH8fL285_dUcIqOuG6qpOcBmFhp599OXbu1GI2borROzVH_PnqL0E8hZ7jzTnOvXIpX3fTtFa_VN3QbQcbDbXOwwcwQXZh_nXudkj6BnE1VKMougpyeK6RJaALhNJtdnaM9rSCI451juqcO5hQH-OpCqSqdRZidLwuvAhTLhRRIECv4LV5jJQohZ6smUAGcQJUGzDvn_eiaSMGA5kbNnw88h-eQRaL2HQFZ1MBn3N9COOpVfSoiC6TiOgCkExDp9nXDbfWceyd-X0nBaQTrUzwjUOk3TbRLZthJiRFAVfN1msvCGHm3QX-fLJW0eLy6XMIETx1nNudkhdhRllgw_wOeExkhwbTNQsUeZXFKoO4zxEH6QZm0bkECmHs66U5uDjfwe2JQl7hBYUCvX4cPvLIQk09JTHtM106WsonvIb6n0YQxbVN1k1mywvZYpuy_zcsqT0y84RL4QMm9-eoOqoexiOXjKAdkzmdAGfh96NG8rYNdLU0l_lIAnzI2-_qApWKkCAD0cadIHPp6lfeIpHOfbVXR5x_3cAzfjpJW3tvWFXZZ16WGVAzt3lHEOKYyIy8RCJICcvSHJ-ZBIALTyoqtDxYkolGIZmPEPWp0ydJlFDmvzaRLJSJkrW2ZnDP1sB3UMLJ84_dAqGtu1h8W-rfhTSz0vfM5TqokH1oSic0B7bDseSEwzPqJO6IkF2HNIeRZucmhOYu8GCOZP4mU3OT5QRXsSB-XdCcMxRp9cFtw8mHP-5OGJW9hrQe08MrkUCY-nRW53C7SAbPSkZRTVdGIRIz-l7CAhXl8XabdTGUf_zEqFXJHXmUe7O1htfu0jNiEw_rkNy3P5twpxXt2jC9lt_C14j7_t6tJm9zhcZbnjR3jEeJBE1CELg5Pxqd8qRqlX3PQfpKdO9EvkEKf_-cUVE4-PX43sjP46Fmf84mme",
        },
        {
            "id": "ws_0afa1eadf9c68e50006a143167aea4819a9c856fb4aa12554d",
            "type": "web_search_call",
            "status": "completed",
            "action": {
                "type": "search",
                "queries": [
                    "Trang An entrance fee 2026 foreigner price Hoa Lu entrance fee 2026 foreigner price Mua Cave entrance fee 2026 foreigner price",
                    "site official Trang An entrance fee foreigner price Hoa Lu Mua Cave entrance fee",
                ],
            },
        },
        {
            "type": "reasoning",
            "id": "rs_0afa1eadf9c68e50006a143171c808819ab41a1083d8e4d99b",
            "summary": [],
            "encrypted_content": "gAAAAABqFDFzqOeMPNi-5CCJrfh4w72ks2A4oS5WX7L13j9Z6FahKqMCjEWnDBmF4U7SDt9oiUU979CgT6sm4XHOoS5BxejQuVyziBfQ52FAlyp2R3lb-SB2Rd1b1eefg2KJDb9NGlBJgs_AP2bdFuUX89k7fnxXxD3_5y4IqGI72UVr8QDN9DoC_zPfqeT0-p_kRB4Ue6p4MyQU-7vSqHetMJVClorMrvWZgIkxwFY--tlVqM2U4wP6YGm8KigDun-ApBWyfS71troFmELi926e1lWPpK2LcCDDDG69nxkDiusW1UnjmgxDmzksoi_Uyt4fozkyzxWK46WayJedRM4e6Qbdy-pDiSXlM6djePAgC2TtbgFQB7gYC8MG-V_Tw5pSVlX3OnRM5PXZ9pBBJmewFh0SdDCKMfAnM6IQhKE4sGx0KzKkKeQx0AK0FuEP8U3JbGmbjiwr0JNLNbV6us2tuAsJ8swYKlMjyG7sbaimAmiGyTr-11ZzJRI-89LbIVGS6IYnm51O0AJc6TvCJgs-j8Y9lW5TbUbbrEF3J1f-XaevQydPD8mHhw-8Z1Iy4wMYZMcqeNCIeermEzQJX5tDUsot_JOOQdHhCm-qbFaKXeS6Mr855oEaUCaX6Dh34j27ErITST1DuHH94t4iqjBYvX0NCjwt0IsAVb8G5OmOLscC43nQ2ciDM3pRQbMuVClD_AJVQQeN3grsWGBKHr06BDJx_ufosdhyS5rI3XpNdDY2glCSsjdQRVQqN3TgFmwI60w3mwVecbuPv1VguLk04hCW03QX823CGbUMDPm8NtAb8znRxhaHJ_lJGN3Tdvbtc9O-wIgyf3rJdSlGt7QTnKWCW13ZW-QQfOhpmfwZRwiSyRU1QVmeZ9gKeZqV1Tegxu65ADaUmPRK9O_JeZaCCTD0zNsqCx7zmmycp-VcgOrhlTLUN-LezDCzdHNZnzA5b7r73bIXJXqJfRErQQoHzZRbWGGFx2RxM5TW9CUmbZlcIlyq3hI7Zyfydm9-ai8r6tNZHONX8oVLMu8wsddtI4Wpa2CyyWGNo8o_h5FB7XbcxM5G1-Jec-xoYaqU_2ZgWdvjtrwenb0K9Q_KzQhHnh2Bj2mAob6DkG-CVLCpDOALx_LdLEWhhFMjWT5vtl_oIvJYWh9iBE4os8Dvp6C79V2nNtgQjdvRLjPz6MAFa8GBRnh8JyoyYuX-gIv5cmhlZ7ExOMj7TaNLxkf_1ctjWe56pW2I3DVjRNCuKbNj3DePK0kHDGbWMn4CANaKbyabB_5kmWITk2wd9EJ9uexz4Q7TIbACVkyHD6hNmpFNUnvCsq0r5PY33DeVtpiacugQOZoS0bTe2KpqTM9lHIAkUU6vMoynzb6CHGmQdnryJVQWHFBfd5LoRx-z7D2xgCQ7XTTkGSbSjwN5d3GCneeQTzEhkXouf03aptMnuSBmnctddbOAif2_aWAc5niEihqTai-U_K_yIMDxuqatjtuDZJcXvcMBhpPHRIO_DicxhNMmdkUqfUEvBz4hoWQXChs5H02lBfccseR2x7E1qYkSgs1eQhZ0j4gSr040ZUZBDOqNAT8KZLo_zTxsTRkbuWJ1ovtGv3iarOMFFyPz0ZmxoX6PMNawa2goE71lukrupb-N7msI9SQxqgHsT6jfLRmw16r_ThvPjQDgTsX5kUFNxGSuN-XkjOzVHH5hNrwzs38ayY5JRuyHukHTvApJm5Rakd_5jvcEMXds25Tq2XeQxkj2U7IVd7hbURME-fl6FZAOaOaJ5CfPZU2X2LeLCgDQ8t35AJkbvLQcbXLudRRWsHEBFvKO3RpZOjk9i3jVcPHz-zCLZPTX9iUucLVhzQlUJvFfC81_MKgw45ODZtj3M0PImbR21yLzFBdfnGxn06QreCjNvRE0HDxn3JM2fDlBIVVbWFNioixl1iHN3zxXqiOppQL282ovzGpOrf6hNOsNHqNa0LC9xhlislbxB3IZcmVEqw621ReKVY3Yq-JNBFag1WlWc1mgjUTxwevYDySRvXGS_N5WilJl5CidfKgTowAywW_Qr9jJAFguE-CfCicwfp6G1H9STVd02xpXJwoAaYeGcwm_7azY72DrADiKAX04ctLMKok1o4zcqp0lKq3UJ-Yc2jvPtAuFelwb7OZERbhCqWq92YCXsucvGV1E0AnKfFTc7CjVj2FDz9mj6rLTXN852L1Mb9Eh-jA0VEvD1H1YZh3546t5GTGeWOtTxIfKLLSD2HTluiADA9-3TVheIdPKMnkr155o0LF70AsBlZyh7kfDrx5aQAcImlaISLvHI2unB8DXhozUCaRfpl32Lp8yQmajhc1_kerKpHWQxOmnKIDSV17G-iRduHUTxJnWiIhIsTY-UPsO-EJ20CdZpHtr5JFYFEq_dq0yNVZPwI05V8BJSnE9Oj5GYOClNEIkc-OD-B69Ti2KbJQAA-hFfz4gL1Di0MVnNpU96VuAO9mW4V3mg7wfZbj_yoYzHDHOh4WGouGBtpur0mokmZm5-50bcHdcUArCHBf7ZjV4IHdkFTz9KytWvAiU3hAmxKWjPSn25jqpR40gCPNXHT0pwJ8SM62PVuAmZKvrsVzdkCwO3ukxCsfnkNafhKWHp5-Ne4nc9JM9FnXqZTYR6SmjoXFuQbStshkh4qHv2SB0DXbMxp_qV3g_P9EcHSh2c_v5kP6AwYPalNx5k7FaPG9gAaPIBx2HjNBTTrXN8iiP60KXbQA3OM4BxHusys-ALl_Lgz5DfvgY6OSkrE6TRUTOnlORA8dn4Hdwk90UQ5kypL6dijRNlJgSobi5Br5thln4w7DMALu5PC8OJhUfiLGjQPj41UmSlEtHuTyrsBC51YHJcgoZwghswUre1BJnQgDNdnnKaK8zxLPcJFbUUwCAn3DV2LGUkhA6TsitAJhyLC2ciliDJJLWwgLy9ohuUZveWu0o7qP9LL2fWmTg8hWbEzcD-a807rXfZHjNu29UTN7-JlEgFB-ISQPwWZMs9DLf2-bfAh4zmjtoAEZHEdo6IKrOf-156TRUmwKzNlTFcmdjJ0R2FAmd40YUNzxe8Niy70zCJfIplDN2B6Q3ZRsPfPWp0vV2bFNU9kbKhjsYGV2FksrqQf-D81z5am55v6QgorSs2G1wOe52sUwa9Ei5JzUxXIN0IWy2hMfKzHXDGkEIanPiEG3pVpLCa9THVVNvmYdW0GxvmVDKsd9B2Nvrxv7gdg5XcEIVYwCFxGITRXh0YAE8rYkOr08SEwt56Dv6kCh-tz8b-FV3xZFf5phULYWO4NzIq-ochjOsJubbZAfmPiUL6fEw-VypzvITg0adIwRFRvlxhxVw_f_rYwDHy_mL9MihWIZ0XwZ-P-78LMRqWX2Q8uFOKBpV5tMAJ7xYqEZQo_HWMOg1Kv99hS1SM_yF7Sps1vSVbpi59r9pH7D4d8xT04ItVM74qj_FovxeUOkoBBWPSn6rdDHY32fhnpLjq0RlYjMqaHw5e-0FqOoVzc3x7MDdkSsyftoAdcSQ6V-_wjOE-TYdUItz-EQFB0y5NcIBMRvCvbDQvN95vbjPdZwle9azY0qd-Ghj583Ejc3O_ok3yPrOqVLN6Eu-blnjRi7TxJFPDX_BsVsTSzhbbM2EybJg6HOqzIFYyJSLqGQRz--izwcOpljqdndzJcDF9zkLytpC-ddjHrPJAhHDbSCQEMwejcRo2IhWhfJAYGyWqSg_HyGJO4tJg0ByMsTM4n14WwJhoBpInpcNv6_YlOQTCBuVITp-p4jN7WhqcCg8uDSV3jkUUTW8eev6dKPnxu6HFYEMCW-O_7auOz4Uc8E3EI1oGRnDiIiPagviODPWxeYWICInc9JO8xX5GNVLuACJay00kGjURS68RHsnPKPSj72V1Vws70paPR7MZDHycky9n_iHYkOY8XyXtlghBRSyPewiYZ5-idDI2Qk1mRc2k0Lm8BP0V0dT1Cu8j8U-jkd8ZMI65u1a97F5W3C96h6FkDJ4M9F0O-FTuJr6hvemwfB-46C6hL05k7hdf_9f5HYOj0lutgruCQTNqVkVYAjzJL9rzm0wZfD_2bL8mR3_TAatqCFNR6jt1r_vvbAImPIZ9vqw8yJnghUWeV8M43zMPhxQuwlAh4BmRgCZC3dAW4zBFXhAY4M5zmvdiLRZPBERpFSXi1JhDvOJsrd9Ek_uN35fm0Oc70uudaGdsbF3T5F8PpT1MtgNDVcRxW2n7edRS4s-5Jp8VS_GfSFpYCGw4q1gd4s1nNjsZ42HN_KGVrKSqu4AoICiFshcXNi9ai0XdN-eKbdUpNWtIy999zSzlvVS2BSNJtRkn5G_f8gvH3n03A2vZrh-_i2A82TJlV8qmtpfSbHpNrreumXdkiesP43LLJyvl-px2PQVlyukbBeVEpoxs1sj-wLvUMdwReFSiLLJut28QmkFfQHjrQIFbR_ata70VhQDmW7JMf1_ZjpBpUvCOhJYw3VVufE5DqBvmzYkQOKTJPQZvTVIJHoK5YSkiNJ0CIFuM8MqRNq8wVKcFB6sYGdbPPY6waPpCl38EotuvhzvB4OPlnYh2sKVF8OFX5EDP3kkM4tl0gcelZ5IByqLbFuw02vepZ9G4J0v8eQ0batR2FiP6J3p4qwyvA-o2xH0fDqGbM1328LW1IJUtGHFTylYI2pZFFPYOcEavLoMdw3YYAtgwA5JtlAQzj-9bmklttvLNI1vw_XZj1kZ_-fTNf9u7eW0wkJ0_DFzSAPpgbxKGht6Ih3aqtU3Tt6X9PJzzTiouhibYRmEtwq0vdE5fZRfcmnJz5-kH_WWapPIZvZnKj9GFs1fepgJEGpJBgmxDRh8gcN21PVD__2PwYAx83pT-0WWwXTEGSYXwu28V_h0QlS_XMDs8P5Od3U33NgKlgoLc5HiKlLKfx2-Q8CSJANf1p6KLJ9LGUIvejGJbkiaX9hr2dWgqt5tmlyBrJLnf5cbGXqwm-Jom_JbbuhNDUfFbvENa3DM14l48AT_yKltInwBUGK8Mf_oLAIebViBwZICk7cWvhftF3w9I7wZ4EbM4dRXds5_k2wIWxo0ZuudMgAZj2p-uzaBxoYMnG4zPOxiJP2riFSU5hC7e2dpjjsTheE6TYzt1QQV-eorhoIuSdpn8OXMv1BTxrURe00x3WFeQC1wCuHMh67eM_agRdM23NU5lCsW70hMRqkqRy1cO9NOdwZvsnRLuQApizDLiixDVy51M_VlMQWxhPlQidyHdW09HB0AgO6VpDJTi3YlLfRgpNP0vXnHFVx7Ny2KzKTEYbmTe7CeoxsveREbJFydwvpvPoN77ooTJUQK-IJgwBNHcDG4eVc7w_8fBzAxPgV2fi7q_e201bFdvSREpC-WIvDaCcN3",
        },
        {
            "id": "msg_0afa1eadf9c68e50006a14317334dc819aa9185bd0f2e87f74",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": '{\n  "block_id": "A2",\n  "task": "activity_search",\n  "area": "Ninh Binh",\n  "date": "2026-09-22",\n  "candidates": [\n    {\n      "rank": 1,\n      "operator": "Ninh Binh One Day Tours",\n      "package_name": "Hoa Lu – Trang An – Mua Cave Full Day Tour (small group, boat & bike, buffet lunch)",\n      "price_per_adult_usd": 25,\n      "price_per_child_usd": 18.75,\n      "total_estimate_usd": 87.5,\n      "entrance_fees_included": false,\n      "halal_meal_included": false,\n      "private_group": false,\n      "duration_hours": 12,\n      "source_url": "https://ninhbinhonedaytours.com/tour/hoa-lu-trang-an-mua-cave-tour/",\n      "retrieved_date": "2026-05-25",\n      "notes": "Children aged 4–8 are charged 75% of adult price. Buffet lunch included; halal not stated. Pickup from Hanoi/meeting point per operator."\n    },\n    {\n      "rank": 2,\n      "operator": "Tommy\'s Service in Ninh Binh",\n      "package_name": "TRANG AN – HOA LU – MUA CAVE (best selling) motorbike tour with lunch",\n      "price_per_adult_usd": 25,\n      "price_per_child_usd": null,\n      "total_estimate_usd": 50,\n      "entrance_fees_included": false,\n      "halal_meal_included": null,\n      "private_group": false,\n      "duration_hours": null,\n      "source_url": "https://tommysserviceinninhbinh.com/package/trangan-hoalu-mua/",\n      "retrieved_date": "2026-05-25",\n      "notes": "Lunch included; caterers can handle vegetarian/dietary restrictions, but halal is not explicitly stated. Child pricing not shown. Best suited only if family is comfortable with motorbike-style touring."\n    },\n    {\n      "rank": 3,\n      "operator": "Vietravel",\n      "package_name": "Ninh Binh group tour option (4-person rate) covering Hoa Lu / Trang An / Mua Cave",\n      "price_per_adult_usd": 99,\n      "price_per_child_usd": null,\n      "total_estimate_usd": 396,\n      "entrance_fees_included": false,\n      "halal_meal_included": null,\n      "private_group": false,\n      "duration_hours": null,\n      "source_url": "https://www.fiata2025.vn/pdf/Hanoi-Travel-Guide-Vietravel-E-book.pdf",\n      "retrieved_date": "2026-05-25",\n      "notes": "Quoted group pricing in the source: 4 people at 99 USD/pax. Lunch/halal details not stated in snippet. Good fallback for a family group of 4."\n    }\n  ],\n  "entrance_fees_breakdown": [\n    {\n      "site": "Trang An Scenic Landscape Complex",\n      "adult_usd": 9.5,\n      "child_usd": 0,\n      "source": "https://vntmientrung.vn/ninh-binh-entrance-fee/"\n    },\n    {\n      "site": "Hoa Lu Ancient Capital",\n      "adult_usd": 0.8,\n      "child_usd": 0.4,\n      "source": "https://exploreninhbinh.com/ninh-binh-entrance-fees/"\n    },\n    {\n      "site": "Mua Cave viewpoint",\n      "adult_usd": 4,\n      "child_usd": 4,\n      "source": "https://kampatour.com/mua-cave"\n    }\n  ],\n  "search_confidence": "medium"\n}',
                }
            ],
        },
    ],  # type: ignore
    text={
        "format": {
            "type": "json_schema",
            "name": "activity_search_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "block_id": {
                        "type": "string",
                        "description": "Unique task block ID, copied from the search brief.",
                    },
                    "task": {
                        "type": "string",
                        "description": "The search task type.",
                        "enum": ["activity_search"],
                    },
                    "area": {
                        "type": "string",
                        "description": "The main area or region for the activity.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Target activity date in YYYY-MM-DD format.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                    },
                    "candidates": {
                        "type": "array",
                        "description": "Tour operator options (2-3 items) with pricing and inclusions.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rank": {
                                    "type": "integer",
                                    "description": "Ranking based on relevance and value (1 = top pick).",
                                    "minimum": 1,
                                    "maximum": 3,
                                },
                                "operator": {
                                    "type": "string",
                                    "description": "Tour operator name, company, or 'direct/entrance only'.",
                                },
                                "package_name": {
                                    "type": "string",
                                    "description": "Name/summary of the package or offering.",
                                },
                                "price_per_adult_usd": {
                                    "type": ["number", "null"],
                                    "description": "Price per adult in USD, or null if not found.",
                                },
                                "price_per_child_usd": {
                                    "type": ["number", "null"],
                                    "description": "Price per child in USD, or null if not found.",
                                },
                                "total_estimate_usd": {
                                    "type": ["number", "null"],
                                    "description": "Total estimated price for the quoted group/option, or null if not specified.",
                                },
                                "entrance_fees_included": {
                                    "type": "boolean",
                                    "description": "Whether entrance fees are included in package price.",
                                },
                                "halal_meal_included": {
                                    "type": ["boolean", "null"],
                                    "description": "True if package includes halal meal, false if not, null if unknown/not applicable.",
                                },
                                "private_group": {
                                    "type": "boolean",
                                    "description": "True if offered as private tour or service, otherwise false.",
                                },
                                "duration_hours": {
                                    "type": ["number", "null"],
                                    "description": "Duration of activity in hours (may be approximate), or null if not specified.",
                                },
                                "source_url": {
                                    "type": "string",
                                    "description": "URL for this package/option (from operator site or OTA).",
                                },
                                "retrieved_date": {
                                    "type": "string",
                                    "description": "Date data was sourced, YYYY-MM-DD.",
                                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Key notes: pickup/meeting, lead time, seasonal info, child definition as per operator, or other restrictions.",
                                },
                            },
                            "required": [
                                "rank",
                                "operator",
                                "package_name",
                                "price_per_adult_usd",
                                "price_per_child_usd",
                                "total_estimate_usd",
                                "entrance_fees_included",
                                "halal_meal_included",
                                "private_group",
                                "duration_hours",
                                "source_url",
                                "retrieved_date",
                                "notes",
                            ],
                            "additionalProperties": False,
                        },
                        "minItems": 2,
                        "maxItems": 3,
                    },
                    "entrance_fees_breakdown": {
                        "type": "array",
                        "description": "Breakdown of entrance fees for each major listed site.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "site": {"type": "string", "description": "Site name."},
                                "adult_usd": {
                                    "type": "number",
                                    "description": "Entrance fee for an adult, in USD.",
                                },
                                "child_usd": {
                                    "type": "number",
                                    "description": "Entrance fee for a child, in USD.",
                                },
                                "source": {
                                    "type": "string",
                                    "description": "Source for entrance fee (official/OTA/other).",
                                },
                            },
                            "required": ["site", "adult_usd", "child_usd", "source"],
                            "additionalProperties": False,
                        },
                    },
                    "search_confidence": {
                        "type": "string",
                        "description": "How confident the system is in the accuracy/completeness of search results.",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": [
                    "block_id",
                    "task",
                    "area",
                    "date",
                    "candidates",
                    "entrance_fees_breakdown",
                    "search_confidence",
                ],
                "additionalProperties": False,
            },
        },
        "verbosity": "low",
    },
    reasoning={"summary": "auto"},
    store=True,
    include=["reasoning.encrypted_content", "web_search_call.action.sources"],
)

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
            "content": [{"type": "input_text", "text": "đổi sang double deluxe room"}],
        },
        {
            "type": "reasoning",
            "id": "rs_0c2b0fbbb0eabb77006a144bd5ce78819ba1838870db5205e5",
            "summary": [],
            "encrypted_content": "gAAAAABqFEvZiZMu-PN6zJpwGrfpGaulTeNw_mVsASIVT5RB9tNhoz9gyFL43qAwOusCkZ2xiGSMD3ulW2SRV4a8Di3rwTUUZO0OyzZ2ts8nJHntTG0FToEHseXkL9-tQEJuzgBIy2UF4fJW2OFqd0Jsp52lvOyeSkDTdoMQ6ru3ahZX9dp6B97NFQ-X4xCVMYVgeao5d-BvZoz8HO_QNaNsrF9EdqeKRskLlSWNiKBYhQizWgmkmyNnlhzyY4ChiAopBAcUujNEQkAuFjmyru0PGdCfAJrBRkEJ4LdmYbBjEdR4y0evLKLadW4G8uphMU3tWtnyP6RXsJQvgsXCqJIbXODMm26cfJ63x0VrtJvGsoUCulzbY-OcuhSxC1nxUZ8lNRyWu5Gn1VsOB1mX9bnxHDSmqMOZ1iFsh_7Ak7cnqygAcUdgYQPgjg_tnU5cxyC5lk6nxoNaOLpw5GuDQ4U3VI60-EBM3v9mlaVcBHsgSdsGoWCW1yZEZgjt4McbE23LHP2NAUgriTkahgtt2QdtWVOv9IBjwXGPKZR2NkCOX7S_im6g6E5Sb5KroVF1pEBLjCoXlkbY_CB6mL1yjQVmbJOIZqeuG2VrqVGIZJeRhCaz7VQiDdHVNWloyrFUZ_b566tBQqXyaj8d_5fEEokE3-dd-QGECjYtSpEGahbuwgzYzUv2UAh4cbnA5E4XCqI0brQn2rCKhGjbOwFWGMsC8PHtrzw01ZABAIKhNyHLWbLO2Qf3cfPnag2ECOMxEISbuZHDjl_T_AEdrGYliz1LCtzKz8YMUoDtbwevX4x_lRRmxrtXMaoMCH-hzSjjT2KQ9Keo-gH3d1MMNdioYhKlwgatl3gMwBFKUX2HzKzUlvHLsBpN4SpIJpxNjNp8hL1rXQ1P5R7DwRECXBBHGt616tzmypgSQ2s08Slxb_aZ8IQ6eXX32ulxBXrF8wQmcqiAPEP5Jjrjwjd_9p2I_iLrmr9padfP3e9eKZJUrSXtXKwTq6hn1LzBXz15rB9JCbnAOTJ6xTKlpi1VCPoQ43uoGm99vLT67wBJZbAr6NvPU2b-NUz8mUh3Sd3OuXetdFlr3r9PBKs1fE3wJm1OxCXtOj2Otdj1neK6ESZke-x1lSjkOoYQmtrTUsZjz-yC0UrTdk1oxQs2rmvA_wCa1z_OK5dxkATlpiD0fDYZwIdt4Vor8kCwYUXsenVqWF7raBjBADsY1ISwobMax_pF5wZWipZS4Yu6P4HL4PIzuDzZKT4x2KAjxKNyYZ-bJ2eaDZ_Ye5FUD94kjPY3XTOawW292Ol2Oxzhh7eOxBXPcXPMbUF0jm_LMMFBGV2ou1L9gnbkwT49JT0PCm0YO8uH3s11TIdqFA1GokwPMGCuo0ukCagYM7dctx1e_KRP5bHQrgZTIF878oNFi-GA8DeWCTUpCFlWW_Kl3JbW3f5Deb0jbFZTCyhkdBZPhgzMLoA41Fu7EDsdMpnC792vbJ3x6iLWlpalRKPxHAXH1nMBO3j1XtkxLBxArIxiTZHbAOTSWP1vGOO37FPoKU-QvfFf0tGboRNo3dyn6SRZGak87bsdZJjOa9IorxStiBlklJaOBa0_07_rYEj4wo8-acRDWVPOqd2Wrp6nQn0JsEPNMTy-FnKWQbvZ2ktuPXhNz1Bk9oadP0KrHXwRbz7HCNftOCtUDrGSSI-qeQtsvZ_ZYw5E0Maq4FvLr9vdtJLuh8mpAezqZc3doHpN-_txwIkacvg8pKHuhNKu_ySeDwtSCQ2D_Z2U_S1ffqoRUJqXjtsTFnA0qdVuFfr7yecOn0tFG2MgC0oStqoJGxTrtxYxLXMNcdunuXjKM1RgQlj1VQKkee_Z09rHywB0bjloitQK0kxYm9KEivHoFCnfOOhUBPMpuW6kxi8ZDLfqcP52Y-6cjhB4HYPcC7sGwewPEqbNYcOMKfuL4siGqr--q9ZFU1t69ah0YFN_3iVDaTGPDh6h6Yek0u-qyEb8JvZWwbL8cosBtjlBg6xSPGHXcXw9cDasrJEeRMJRoOtD0xSjji2AaezH8IxqBi6F7UWfjLxjdtHxcAKkCuUpYpN7_KnF177LASpa1rk3xX457mxCKGvykj06WgAMUm-NOdoNbZDFoyqB5Cd4E6r93-BZFornnqJgP0NqT0RYBj6pmd1E6YhPwhAJRR6jz_G17xGQMPENNzd3SqLor5tCuXy2MjEt8LoATyDYW93HgkJ2dcEF4Kso8usu14Puf5BjzeT3tzylmkzlBupsvuRlhe24LOU-G0IfpG6E4OpigSlN7-3iXFk3BLZoWPH3Ws2PQ_-iSXXZ8eY7ZgEOXzjnEwlGgF1ky60vdL_SUSbYY6O3sVpO6HaTM4x6PGDK3kZB7OV0OY9KmOVILSS62KMnqAj8tnNe6umYhe_to12qrs05RxUA551yFk1GOIJ3NuDZJ5wcDwS5QKVTMWtOQqCU5tsO_vIWIeT4-ur88Pa0bcS8MfT_7TXMCs5O3ui3ifM5sg41BFgAdJ1pF--LB8P2Fz4dtbfbrOgXBifFmLWacSOzQl4qzWUS0QrVG8J6vrYhsrnr6ySrFF3iesSSDmbtGSvXE-87X2oU1mnrgxdtkmWDChUIVSJlsVXi7wvFtPRbyMVWhCMWnBvduAwjjVtj9q1ikw7dhFHm0rutZiJ6utKmTbKxQuYx_euohOOj_Ph-RbKxN1cjO4st45Ynav8FLfY6KCYCWAlXoW9NmxDkO4sX-X9GgKIobFPsoaDuy0ghPeesiEr5lcKckyv3tLfysmQtAD8LZTv4ApekjVL6AG6T3Hlde-t24R4unACMgekBzFUyNfGAeibMPbniOhkVhrPQ8dHq2gvCoyc_FzGbfO_AYBV3Ct07s7_K6XPHwzXd7cQj3NwMup9Pyj27dwfuMWD3TxR_ohLY2pAuCM23QKDeSMuRfVV6O4MxogKhlhO7cKtHz6xQ-ArJftLuV7FLWUHxwUwDlUmgFogboXMz5arA6kFxb6koCLxJEKaFhVaj1XYmVcQGsNWnv1qafaklMMOWt31AV0nFmNppYhTdSIkgN1oSubo7KNtkxt8qHlrCayq_VY8XiwIaFQIcOJ9epnlMba940f56PFjQZMV4Q0qRmgDFjyiNdi_RS1wJP_GcjiUHKD17tqvjZXa4m0xIYVwYpn758lGY4RiloErO9lH6yOtaIuvhNDUZyputqlIyzuCV6izqnjvf_WaU3ZeEcGhZ-ekn4CSntYmhFWsMPZNiuvlwcR8r9WhP653h5WcJ",
        },
        {
            "id": "msg_0c2b0fbbb0eabb77006a144bd8614c819b82ef192323b21e81",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": '{\n  "block_id": "",\n  "task": "hotel_search",\n  "destination": "",\n  "checkin": "2000-01-01",\n  "checkout": "2000-01-01",\n  "nights": 1,\n  "passport_required_days_before": null,\n  "early_checkin_needed": false,\n  "late_checkout_needed": false,\n  "vip_treatment": false,\n  "candidates": [],\n  "search_confidence": "low",\n  "search_note": "Bạn muốn đổi room type sang Double Deluxe Room. Hiện chưa có đầy đủ brief (điểm đến, ngày ở, số đêm, số khách), nên chưa thể lọc khách sạn. Nếu cần, tôi sẽ map \'Double Deluxe Room\' vào chuẩn \'Deluxe\' cho 2 người lớn."\n}',
                }
            ],
        },  # type: ignore
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "hotel_search_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string"},
                    "task": {"type": "string", "enum": ["hotel_search"]},
                    "destination": {"type": "string"},
                    "checkin": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "checkout": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "nights": {"type": "integer", "minimum": 1},
                    "passport_required_days_before": {
                        "anyOf": [{"type": "integer", "enum": [7]}, {"type": "null"}]
                    },
                    "early_checkin_needed": {"type": "boolean"},
                    "late_checkout_needed": {"type": "boolean"},
                    "vip_treatment": {"type": "boolean"},
                    "candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rank": {"type": "integer", "enum": [1, 2, 3]},
                                "name": {"type": "string"},
                                "star": {"type": "integer", "enum": [3, 4, 5]},
                                "address_area": {"type": "string"},
                                "room_type": {
                                    "type": "string",
                                    "enum": [
                                        "Family room",
                                        "Connecting rooms",
                                        "Deluxe",
                                        "Suite",
                                    ],
                                },
                                "price_per_night_usd": {
                                    "anyOf": [{"type": "number"}, {"type": "null"}]
                                },
                                "price_per_night_vnd": {
                                    "anyOf": [{"type": "number"}, {"type": "null"}]
                                },
                                "halal_dining_nearby": {
                                    "anyOf": [{"type": "boolean"}, {"type": "null"}]
                                },
                                "family_friendly": {"type": "boolean"},
                                "source_url": {"type": "string"},
                                "retrieved_date": {
                                    "type": "string",
                                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                                },
                                "notes": {"type": "string"},
                            },
                            "required": [
                                "rank",
                                "name",
                                "star",
                                "address_area",
                                "room_type",
                                "price_per_night_usd",
                                "price_per_night_vnd",
                                "halal_dining_nearby",
                                "family_friendly",
                                "source_url",
                                "retrieved_date",
                                "notes",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "search_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "search_note": {"type": "string"},
                },
                "required": [
                    "block_id",
                    "task",
                    "destination",
                    "checkin",
                    "checkout",
                    "nights",
                    "passport_required_days_before",
                    "early_checkin_needed",
                    "late_checkout_needed",
                    "vip_treatment",
                    "candidates",
                    "search_confidence",
                    "search_note",
                ],
                "additionalProperties": False,
            },
        },
        "verbosity": "low",
    },
    reasoning={"summary": "auto"},
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": ["vs_6a14381af7888191ad3ab11eaeca95b0"],
        },
        {
            "type": "web_search",
            "user_location": {"type": "approximate", "country": "VN"},
            "search_context_size": "medium",
        },
    ],
    store=True,
    include=["reasoning.encrypted_content", "web_search_call.action.sources"],
)

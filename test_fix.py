"""Test lại với 10 cookies thật từ user - verify fix."""
import sys
import json
import time
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Tat ca 10 cookies tu user (cung thu tu user paste)
ALL_COOKIES = [
    # Cookie 1 (OK)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"v%3D3%26ct%3DBgjHlOvcAxKcA9Cp5eCQ0uAbIK375r3I072z1v9ZHEe8qOpvvtOpgNxdLVrQ8wr41Hwm7Pj-ruSS1jT4aeLJildS-OoV1-bsoXkt09pVQvjFW5B1b9D1nbRjVF2Rad4nYn7Mjc2EeTbm-mmEPqDllNZBsbNlG8lSOwQBrIBTGqDAKGEPnrO5cSqgEIXSqsOqhWePNQUyvnlVmBN4FFWXcNk4PuAG9gD4oVu8-jEYRnHOqrgW-zJ8rExH-hIibDGYIVd6UipPlwH1_iCzaWB4koEXs8kDmOGn6VoFjhmTjBct8itdbVBB5qU4hf1rHFU5THh89eeKHQz0zuo1zYT5kFenublcEEtgcQ01MFNhgXY6X6WQEyr4VB3znu-MVhxOCiva-JshkcoNiwU7g0sqe8GXUQaJIEVoc4Qq0eIoD7TDKOoqsVGWkk-lBXIsW7xw0b7S7VkjI5kby5WB02AlJJ8-YHhOO_JYMOHWXsvWqUiWvoMu44LAVNhR6hOFQhrJ82XTWueU5hIDGW4ttNxkV-vW904yT1pf6xmPTDpztGMPO84OpAoYBiIOCgx1JgUKsfqhHu80GO4.%26pg%3D3S66EWQ64BEPLN77VUYUWFTEAM%26ch%3DAQEAEAABABQv0KhtR8GR-MQmnQ677qZ0ZtoOKtCd7xA."}]',
    # Cookie 2 (FAIL - cookie die)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"v%3D3%26ct%3DBgjHlOvcAxKMA0niEbTiB5FA24BXMgU-LI_GSHGcQDs_-bCPkiatFMcw99N8_L-DLAnZbZ3tmeWLNbtPHe2VQmtlhZB3oGD2YK1OF9aFSGMVS-kegLuxO6JNiHqynoQv984Qx81aM2i21suB1mxTzxxsAYaWvPV7_1zNSx9b5wZIdTe5P6cwjvvpzFeg7im-V8pT9JhNg9stTUESEn3mkaLxMI0fgY3lG87-QaLe5drYByOyM-KME1sSgxExE1PqihbQyLSiWIX3yxiXRjexkfbDzq7BYBKnrF7zOy1xYEW72ynu7j5SnBuGdIQzbD4-K7qToSYzu3eZ7YR6qpUUbHHOWansJ0s1w7N-qG_HQyQeESbfmMtPVdQMDPaRImXVbKYjv7pce7uZGdV1R0IyrNCY-G5F-XwPCgWOwOATCJXECSBX5fvf2CsRAd31v1Q5T0HIHW_P-LPb2aaX_bJy6B7sRoeb3LBrWUFjpxLoW0szeCTegnqxpYpXxYDtrpNDyouilaqH4H788dyoNHbGbNr1XekEGRgGIg4KDGdAJmqxpm0szuVLtw..%26pg%3DA5BEUG3OJFGFLKXZTUMC75V5LE%26ch%3DAQEAEAABABTh2oM86vPYvHkGY8ma7_ylilW6a_BMPUQ."}]',
    # Cookie 3 (OK)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"v%3D3%26ct%3DBgjHlOvcAxL2AkRGDjTCqMSC5rZts0h7lG4UbZXaktvkhRynDghvrfOPKv3l3CH7YUqTX6qfvvDwhgUz0YzkEZkofWwNT_lOgYum8_fU_IlYGoyNxAdMIYKurUUXFUvyZAlnk9ECKuBPeEl0ZdOlV4tF9X-U56F_h_Gi8SSgOR88eZEcwIvouGGF8oxX5YFWeQQdbemc94Hwo2JXXIYmi44nsl_t7Z4W7VLCH4rNN2vC6O9X7qI_bgbvj8ICDlNqTlAT3YU1m9gv3v1UCnLI8vzUoanPrGuo-LnHAFmOHrI_7fGak-QP0kj07JnRrl_-E2DmeWFDBTHrkcqrPkOtIt0OAeuPW9Xf08EK6JLfi7WCqvz9wTR_dv-nicwzeMDBjQEJ4qdPXA5e3_N27OVOduh6C2_13A5mNXGtSSpwL8149lKgoTF3E7YqKVxfxjJit3ryGqgGj3pOqxN5AyQqZxRMGhvB2s3grH64PvpLzxa5r_eHF4gQw5uKjHqrh7kNGAYiDgoMXIkg7GKsSDb-wulH%26pg%3DSK5SHRUVAZB6JN6VYMNEWO7BQE%26ch%3DAQEAEAABABQqXMTlxjC-R9d1ijykzHQPtmEUGa3HPCw."}]',
    # Cookie 4 (FAIL - cookie die)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxKbA_DKRspNXOtg9fu0-l-LpuHk4AxJacveMwOT00POoL7V6Pw7JuC0V7GSPUXrQOr6lE5QLFcsDlh3t1_F6LB9-QTKIrQN_9KVq5G-aLJzxS0MwCVUNr7k3j6oHt2o0NiRgS_JH5gsd63LoSkgJ3PNhAihWfJwIoAsDzfi3IgEvjITosbkp7ih5iL-N2WUE-WpxslwcFp1r7-jrZbtvZ-tjxwcS1Fx_xzfa2nfLfFGr4w1KkPsKecy-py629YkaljcOJKPA55T_QRDRL1KpqVVzLTTtFrWcbOviebnfVLD3tLEiBkBRPRJPiai403fhIJKm9L-BvudblvVakLojw6wuoDLA0Xn6Kj3PHLbV52dp6fX-h59qzQ6LQGnUKGWAP8_OpXx3n8gjI3kEEElp-2CWX5SYpiQjT1hLU9eaSJucA-y_qTYnN9cRWv7YYh7nwpsbRzMGvHCM110dDBWcXlPOf9y9VbcB7JW1HBJMvgiLYGym7ToXZs5BhqvnPGF4nxc8eJqLpJd2ZHYCHoaIMVaV5K6xv6uFUrT33vPUhgGIg4KDPytimBwkpcpcfNV9w..%26pg%3D3QUECRC5QNAKVD4LFK46DEQS5M%26ch%3DAQEAEAABABTqH9PvIm8QXWfwicM3iujnXuJMuIeGYIU."}]',
    # Cookie 5 (FAIL - cookie die)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxKqA0l0o5MbQhnVitsR_v4jo27Y8696GWGn_U0Sz0n_Ua6dtCMBzG8rdvAwv_M-nD-Wk_coC66dbIazlSSLMytD8iksrP4ZresUsmNSdiuDF1WrhyZUEVv2Zxs9MT2Yxf2_xLYs-PpMpuYWL7icR8gwGcaAormyOr6CmK7rpF2H7oNgauebsmAxhWUIc0KHpam8eRny7Aqyel0MnilVRppzv9BGQ9QKO2CSjfLk2-6PjAgWUcMLnzWfG1v5SrwusXoPHP2hCRRyd1gDyIlAqoR_KJrR1WiN5d__n6ZO4VEguGXdZG1dSfpzIT83kUqOR5a94mOamePLE_r6isTt2tIuCLgk5U8gsN--0FYUpzuGvblWr0JzPx8S_m9nwJn3Mg0LQ1mDOg2rDV7Hon1mBVCZTX85V0k5HUk6q-y2ZmiRCdamrpDgCDySuInJBWT05WkXAjdU9nMLGivDvoBlfw9CNad3ntsTNEUHGXEWIBPGdoB0vVQ6_koGShFxxVCepW3Q4poszd6gTMshs01DgTeOxItiZ0wtR2QuJYhhwhN7STqCoCKbRmMlqsJeQhgGIg4KDKcu-A7toWIXbhjxEA..%26ch%3DAQEAEAABABR3dTNwuuCS_yaHkSJGlfXz4pLIQ4RvlsE.%26v%3D3%26pg%3DGGSCESEXYBFB7H5H6DXZA4XDFI"}]',
    # Cookie 6 (OK)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxKwA5dY35mIvTmHHAKKCr-CrM24Ilhsp4TaeF60HPojzreTevR9-hWOHyK-cTSrfdoRMK90aa9PIgaPLEQwRR2UVY8AzgOp6xqMrqpLv0-4i71StveKgscP3UfJf6yRpPR96gvjkm2pq18eM2quFGF9d_P_eG6MrnoUAoYoKYdqoV7crwVGqBHXBZdm32UInBX2DewWwYg2tjWcz6ez-y0NgGSokduLpisgB5S6OO2wcAF5ltxoO5erKuf1-LNTA89oHJPg6drpMwQLuCyn6gD0mla9eKF12frbIhEfdZqNWWDC24gTbM9Ah1lNBvphXOrkAf5oJFSNx9QPtJ7wDY9pFy3qIvRCC1mgJ4GfcEtAB-UPFVvhKkcLTJYkERRvmIb61b5d0EFu8hgWMTg6t-3beJkIsw-6gfXHUIQXs-OHAnS7fCBn0fbVw6CqTAdR5uehEkLuUHegzVfyg2re941Eym8IhTthFOZ5Ph5_bYIXWWvFrM0eg7BZFtFcMUbV6VTV7mpT11_cg2-MivWIhO2FWYedUkcTZd-21q5jKvg6OOpmRhChciYeDDtehzCDJklO0RgGIg4KDDkmvfCMqgjTUqjyJg..%26ch%3DAQEAEAABABSZ0tTABnaSGxnGhk90vCdFNNryRiQtsmg.%26v%3D3%26pg%3DJFHGWCURDRHY5LR2T4Y2O5IBTQ"}]',
    # Cookie 7 (OK)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxKXAwWrpJrsiykqu1dkyDKs2VXf0KhiI0E9xwH2aEDYg9WA3F6TTMsNaJFftev97ZxWMu9t4kA39gBvzpJR9FyW3YVS8VACkq4Oxscy2Xj_jRs-7YKv1HGsalRCtS4v2O4cksnNCY8DjWT7VmAjWc_nESMxHAuZd1RlOLS6-2mcuB64u2gbGU2jnX3OSA8Efofd1cyETdwTk3czGR5sYC2fbEOQ7QEi8vnLomxpeGriatHgVT2NfFQ6uqGxHWDuqwLa_PUjxMelfXSpl-m7h298iLL3N9znZnHeCox45yjz7IVwqcQowuqwDmW2gYQSDl7pKTTSqg9ld6kotVq23n3aaGV9QSwBPtN8ZHNLM4UVRnyPks72rtpfQZADIeZOmD5PJ4TKDy5wtQPxEn7bm2HtQSROrQ503nnDmU_MsCNgyKMHThWgPd01aVxlTsr2NNbnZAylp6ZTrSjW9d1BqXA-kFECoIH50sK5dUGu40UZNScUVImi9GI7J8wROu9SONmmBQivgm-OAdYMnv7bKGzh7a-AtXO6_t4fGAYiDgoMkIYrOFEWd2eH0rCR%26ch%3DAQEAEAABABTQeXMaTUJOOBQvm7MFH7MWjv155colr3M.%26v%3D3%26pg%3DRMH6G4OYVBHHNJE5B2KWKYCXTA"}]',
    # Cookie 8 (OK)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxL6AxgbK3Mv_bxhgFyCec9mupNJIZ0eh3OyJH-Jopf5YTwlCxYWa4LI3bGFiQJrcIPzqilxTg1_iOmfdxL1prJQhm4SimS_Hcz8Ij1jbAK6wIyF7zISm0IHgExK6RrIEJGj3JiltcGRqNP6okH4ve2zHG88o6gR1Er_nuoARbAAqsID8Qx8x-WNtDMGylh2IMy61xCJtzc2db1PHt_XyRBtCbQ0rC0Pe6G-U70Ltd5KlbYqAAXsh9te4WpcvRoBE77VZCVi8gtrixgImBTmM-mVTQuQSsA7ZRJ5W5Rv5FvK87o81zSeRnSUTNlnRQqzlRjRzFr4nn-TYAnoCn3mYGtGfh-08xxwDTqcF6LT8AhhVjlHlF9oKIdFeGhWB3Z-w6FrsmFCC2uuviTgZdLfS7Fb0c_-0Iuy1n0sHxRaDQ11yxFbNslaKD_M6T243JG8IhWVywtrIOtwIHpaj3WJxFor5nd5AFq_2qX9omDAHLTmfs_0O4koeoDV8lcYlgcSUWp7SaFzgAqqvtznocLd7oEudzsICux9dw4J5Vzui5ZXYP2xbnqxeyvi_CBOshMCm2_yjiH5seXVkhZA_-YQOxBUh-vIKbjbbXRlKYMtK1GEvJN_qLV5qpKV-6Uu9u5ou2cmxPejJityR5uNZVUNOflAOuVD4HVlX_x_A6d2GAYiDgoMLvcpxvHN-JkuedcI%26ch%3DAQEAEAABABRzL8pwBY5m_lawrC5cygTOPIGz7ZNMmfg.%26v%3D3%26pg%3DOHT3WZELEFFBBPLQJ4WN5A2H7I"}]',
    # Cookie 9 (FAIL - cookie die)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxLcA0vRfWHgzK5ebVEwuGzwWUqmYBc9HloUOvRQsuFJo-yEqP3uZNV2PFFIS1qUqfdImHgK7l4jRNt4JID4YrwJ4e7erOazgmz2HBeQ4oq3AyQeUkEJwfrvGpv9vPU5IEUEQSkFRGOzNHZyyRSUlFLrR6xmkfQHEPM68ffahHUtAtDESh1cUTcYfZARTL6e7MRFmjDyz7yfpzFxZ2sw9cxmqwZNO5Bw2f6ezy9ens0CoRLASjn3uNjnn4LSBlqUi-VqNSNBbq_dd_OWrOSW6MujVJ6Fwfj5WBvWpUL3b3to8mbEl_45D0bP3nc7aFzkIcmg9GMTDBLFtV156mvOagEwEKUGTpc3MV22DPbu8ieDNxX8PJs2LweKBV48P_Xv7wx6cLbf681utuKKsAH-X9drmwsQOhvDwxLb9toL9rCuc5hdY05ZJojfkDLogH9W0riCR_aJfrtV4bpcVAF7C0eJn7r6OtQ6_k3kyygu3FxzBrOT9wT9F682Grd0HlsUVDZtxMohsQIUSEppWyuOrx43_5s0q-FW62VvO7SwO9586cBg31v7ilkW6VkGsUNwAn_DMhFRHdnmnldhGGymCIkJAWGsVBS51HTHD43mr3PSig9aHHcWcMWgf6SosOBQGAYiDgoMoyECIluo_gHiIvGs%26ch%3DAQEAEAABABT-7qKfE3paX-qE2z2xM4HhRxinZh--T3M.%26v%3D3%26pg%3DJOQULJZNFVCNJC5KV5KDXGXTMI"}]',
    # Cookie 10 (OK - trung cookie 1)
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"v%3D3%26ct%3DBgjHlOvcAxKcA9Cp5eCQ0uAbIK375r3I072z1v9ZHEe8qOpvvtOpgNxdLVrQ8wr41Hwm7Pj-ruSS1jT4aeLJildS-OoV1-bsoXkt09pVQvjFW5B1b9D1nbRjVF2Rad4nYn7Mjc2EeTbm-mmEPqDllNZBsbNlG8lSOwQBrIBTGqDAKGEPnrO5cSqgEIXSqsOqhWePNQUyvnlVmBN4FFWXcNk4PuAG9gD4oVu8-jEYRnHOqrgW-zJ8rExH-hIibDGYIVd6UipPlwH1_iCzaWB4koEXs8kDmOGn6VoFjhmTjBct8itdbVBB5qU4hf1rHFU5THh89eeKHQz0zuo1zYT5kFenublcEEtgcQ01MFNhgXY6X6WQEyr4VB3znu-MVhxOCiva-JshkcoNiwU7g0sqe8GXUQaJIEVoc4Qq0eIoD7TDKOoqsVGWkk-lBXIsW7xw0b7S7VkjI5kby5WB02AlJJ8-YHhOO_JYMOHWXsvWqUiWvoMu44LAVNhR6hOFQhrJ82XTWueU5hIDGW4ttNxkV-vW904yT1pf6xmPTDpztGMPO84OpAoYBiIOCgx1JgUKsfqhHu80GO4.%26pg%3D3S66EWQ64BEPLN77VUYUWFTEAM%26ch%3DAQEAEAABABQv0KhtR8GR-MQmnQ677qZ0ZtoOKtCd7xA."}]',
]

# Test qua Flask API
import app as flask_app
flask_app.app.config["TESTING"] = True
client = flask_app.app.test_client()

# Test 1: POST /api/batch voi 10 cookies noi voi nhau bang newline
batch_raw = "\n".join(ALL_COOKIES)
print(f"Batch size: {len(batch_raw)} chars")
print()

resp = client.post("/api/batch", json={"cookies": batch_raw})
data = resp.get_json()
results = data.get("results", [])
print(f"=== Test 10 cookies qua /api/batch ===")
print(f"Total results: {len(results)}")
ok_count = 0
fail_count = 0
for r in results:
    idx = r.get("index", 0)
    ok = r.get("ok", False)
    err = r.get("error", "")
    src = r.get("token_source", "")
    if ok:
        ok_count += 1
        print(f"  #{idx}: [OK] source={src}")
    else:
        fail_count += 1
        print(f"  #{idx}: [FAIL] err={err[:120]}")
        debug = r.get("debug", [])
        for d in debug[:1]:
            print(f"        preview: {str(d)[:100]}")

print(f"\n=== TONG KET ===")
print(f"OK: {ok_count}/{len(ALL_COOKIES)} ({ok_count*100//len(ALL_COOKIES)}%)")
print(f"FAIL: {fail_count}/{len(ALL_COOKIES)} ({(fail_count)*100//len(ALL_COOKIES)}%)")

# Verify warning da bi bo
print(f"\n=== Verify warning removed ===")
for r in results:
    if r.get("ok") and r.get("warning"):
        print(f"  #{r['index']}: still has warning: {r['warning'][:80]}")
        break
else:
    print(f"  [OK] KHONG con warning NSES-404 nao")

"""Just the token redemption test - the one that failed in test_final."""
import sys
import json
sys.path.insert(0, '.')

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from netflix import get_login_links, parse_cookies

REAL_COOKIES_RAW = [
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"flwssn","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"nfvdid","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"SecureNetflixId","path":"/","sameSite":"strict","secure":true,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxKMBHsYrGvdE6hAKq7mK0Jhjhti1pWth_mIhdXv3RNt_yo2ay0H9PakFLQmHhvndxLArtB2XIPjybpi-g7Sb_QwiXqhMoY5hR456_TvhazEAjYTUpW1zMh2JkKiAfdOb5wGaQabA9JTUYS4FJumftiy1znQ1pWaUaUIS3tKnbqxoGtxL4mGcTug4cpp3rIrO62fiJUVuD_8VMwjoi1-P5Vo5y0XIX3ZCsc6FzMM1MCXKUWhg8M6_F89e_Ad9svNQVLnAbPT0Xc9_4OraknzPelKneQGVH4JxSkKPJLBIILsEKjBnyWiRQ4ANQWRzIY0SGnT8hquS5rZ9Ue53mSSFQVAvjrdAWpmW0azb8d2OsIoo55YkN2kHWLJJvvYhR7zdWNf52Gn4E00R5KjkUPT0U8NSR4eCG00sMTVIe3NwZZFP2ZFUaAF3mlhOE4bSeaCX9K0CN3hVZSdsIqvUAriLxVe1xkqZRwS4RKI7dlgv5FwDGx6PWpmusqs9XYEiZSpl3UbPVGRc_zOQxFuw7PJpnAllYSaNJSLCImkHVW8B2ReLx_UYZ5AM1QeuwWVKqWlBlTSBP036h5GVMQioEl-oJqa830jIzkcK43CFaYL41Ygtwh0B98UXG-Kacg1KSKPXieNHyuSG7dBpndfU4D4u5WzeC8ePGccIegjwna6a2gXdvq01lMYno3WtACtRgGqGAYiDgoMiSu7GlBF0gJzIO30%26ch%3DAQEAEAABABRs47BMh9TCBFax0isxcqbg8oc43XcKrPc.%26v%3D3%26pg%3DMPEVBNSMKVEVPEZFKBHSOICVSI"}]',
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"flwssn","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"nfvdid","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"SecureNetflixId","path":"/","sameSite":"strict","secure":true,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxKuA7TVcf8YegNL00II64nDWdTzj-fPWD6ObO6w7oUDzynZKeHxTmfkBycVSEtjDwZsHa05TEujYOl45YQYdxlwq8ilCX-FVIsXthXGENMRm3hfeddh8LYEM6LBhX3ql5cdr6ChyrYtbBtN0oRpo1twoggxgaNVmw07wjLgIykpWA5nw0ULRCpMeziSJxuK9x9GFYC6A-Df2vuwJ_ZJQNW9ysQyiVQv-CXp5yZ0ExTBCf6GEfGcjPQCn2BXSeA16SIhRXvY0TtQcT_wCYQIYUvxLl23GT6YrckUDdWLg0Q8yPDKyM5Kf84JMSvbTKnYdsHIkr3HcW6Gs7GrhCeTyzWOyI-hEV5HlN09wGIq-q-XMZTtrjQ-xwk9ISrOKcedpDnnqYTn6SNKv0e8XUOSxE99pclVUMsubfKQPznVWox1jsSpNcU9qTrVFwGdCRcn4HfXvdVCNyhVizUzyKgNrxddSUA-4RUaRvGUhYamhaThcDatAxAYEy4qevNpe-YtlVYUvw5WmtwmDkUtK9H_EUAFKiue21QQN3ET8XNYMtKYgbD8_XgciIDkUdQgn9gxVbgYBiIOCgwTigIFR4Fi5csEgJc.%26ch%3DAQEAEAABABREoImZqaf9CfwxG7uhkDjFX-d6UJMvyAE.%26v%3D3%26pg%3DTT3DJ2QVD5BHPFE24WQW74BWSQ"}]',
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"flwssn","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"nfvdid","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"SecureNetflixId","path":"/","sameSite":"strict","secure":true,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxL_Aw1vzkIvuKg77SN_nF-liQh8Eet5cEMsA7XbKBFg4H87MRBP8RpJRXEQWVePUE0esxWeQ-ZDHJ0tvT2JvB7F1-6M8JUktwJN6hfc811djzH78hg9sxjXaF-Lz3mXr7FK24ZsG4i2Z2uHmeEIGBqPRAfbPvvKZkyqd_722r1cZO4EChtuyxRePiahxaXDuV3xcTyErjqes8EFPl-8_TaIcxg2nreUipi_nXNag2iNpqFVJQ9jee0xxRUWWhDhpwfsc_CCfbApvDcbRoZlEQhagMqiEU7zwX0k7C8KAFADN6lNQ3VRZyU7Pg1NYplkIQlEaNAI_L_JoJhJO4uMVladTxvQ4vsWlKwTpoi4eaLJ4zfNWokTTuZTCms6pJUB2xe-o62gxv36LG4uRIAHwCPLhJBGsXkKDBFB-i4TL102mnY8HdGLoxmAEHuLDGq3VkWWXWfVghO2bOsP9BzZKO3rZsMKVwAaRMHtqBo9FVT4pHWUcU1RtPK55NtsUY9YzrZmgwS9-xMWkQeqaKgQHHvOa03HDRdrJAYzZWui1Y3ZWBdJo7hgKyS6EMt4kpKBWsl7sqHDAtcC3Buv_RyPSb82ENnwMDiwbWGoW4BuI2h0iNLiMe7xWhTZJYUeQndPveKeNPfBSuHwT8iBfXuErbt6KxM4Nb4v0UzXXj7Fp6ci4GUYBiIOCgwAxmCiP6oHM754WqE.%26ch%3DAQEAEAABABTqjMNm0nBtBUsxpnPPCNJSgq72sutlRE0.%26v%3D3%26pg%3D7NKLDDTSONBT5CMZHJNRTSLTTE"}]',
    '[{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"flwssn","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":false,"name":"nfvdid","path":"/","sameSite":"unspecified","secure":false,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"SecureNetflixId","path":"/","sameSite":"strict","secure":true,"session":false,"storeId":"0","value":""},{"domain":".netflix.com","hostOnly":false,"httpOnly":true,"name":"NetflixId","path":"/","sameSite":"lax","secure":true,"session":false,"storeId":"0","value":"ct%3DBgjHlOvcAxL4A5V-O_fePzvchmBJYK5PC5jFDnooxsJg8XaOPvNuZazRYg_DhsMzybY5juhy1G7Cy5TD2SHQ_TDn9xlr0wFBANaXmfulyTDboWW_4YUxmXlSxG6JP761MMlytxD3c181j6qt6Y6WIrYAZx6K5C79aDj515CT7mVsAyTXx3mZvq5UcwxDJYzOLlWkYgFioZERb8_iJ1XHdyrEzGmpQn12vUcOmk97AgC8a8_rHPevyL4Og0NuMVvX91TCYZn5E930Z2uPVDpAbyJOufAe7DPQjRfJfDDsyuA4Idha0XLVaoWgjQyJi70rqvNgpTYgUr_rpIs48Wsv1c0DHF2wDQl0Y_4Yn0pUD96k5dZje1y4fW1dZuMK613U9jhLa3FC4Weuluqyr_WGozbapYsdx-JETTZmH1o_4L3hYQRMzR8oysiuXABjxuM65xrSq7zgQbXg6Elsh-f3FWwoKaGC_WNo65nTAjr5aQwSb8hjeLUpJ1bf2Ib7_iykNX9VnIS1Hx0aJhn8X0rO31zc9uaWOKfP1clDANNKvR5Ol7PsHNTG7Iz_LeVGH9RdDvvfeuCybGrJj_1KObZl57hHajgV-q2V8bdH3CF0deS_3Wcq1E6sBsIyBUUj3f-x370kQ8pyFXvRcBRY8QYLGmqliE5KzMP3lyn-kUKHeLrXjRgGIg4KDHIet7gtDrAGQPrElg..%26ch%3DAQEAEAABABRZneIZMnfH4-z71dDvCsj1U2G4vGGhACQ.%26v%3D3%26pg%3DLMLAFPVLIFHVNJJ35MVI57GLNM"}]',
]

results = {"pass": 0, "fail": 0}
for i, raw in enumerate(REAL_COOKIES_RAW, 1):
    parsed = parse_cookies(raw)
    result = get_login_links(parsed)
    if not result.get("ok"):
        print(f"  [SKIP] Cookie {i}: get_login_links fail: {result.get('error', '')[:80]}")
        continue
    pc_url = result.get("pc", "")
    # Extract token from URL
    if "nftoken=" in pc_url:
        token = pc_url.split("nftoken=")[1]
    else:
        token = result.get("token", "")

    # Test 1: iOS Safari
    print(f"\n--- Cookie {i} | Source: {result.get('token_source')} ---")
    print(f"  Token len: {len(token)}")
    print(f"  PC URL: {pc_url[:100]}...")

    for ua_name, ua in [
        ("iOS Safari", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"),
        ("Chrome Mobile", "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"),
        ("Desktop Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    ]:
        try:
            session = requests.Session()
            session.verify = False
            resp = session.get(
                pc_url,
                headers={"User-Agent": ua},
                timeout=15,
                allow_redirects=True,
            )
            has_404 = "NSES-404" in resp.text or "Lost your way" in resp.text
            status_str = "OK" if not has_404 else "NSES-404!"
            print(f"  [{ua_name}] {status_str} -> {resp.url[:80]}")
            if not has_404:
                results["pass"] += 1
            else:
                results["fail"] += 1
        except Exception as e:
            print(f"  [{ua_name}] ERR: {e}")
            results["fail"] += 1

print(f"\n\nTotal PASS: {results['pass']}, FAIL: {results['fail']}")
sys.exit(0 if results["fail"] == 0 else 1)

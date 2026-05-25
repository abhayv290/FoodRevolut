from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.users.emails import send_html_email, wrap_email_html
from django.utils import timezone
import importlib
import ipaddress
import re
import requests


def _get_user_agent_parser():
    try:
        module = importlib.import_module("user_agents")
        return getattr(module, "parse", None)
    except Exception:
        return None


def _parse_ch_brand(sec_ch_ua):
    if not sec_ch_ua:
        return None
    brands = re.findall(r'"([^\"]+)";v="\d+"', sec_ch_ua)
    filtered = [brand for brand in brands if brand not in {"Not A(Brand)", "Not;A=Brand", "Chromium"}]
    return filtered[0] if filtered else None


def _build_login_device_details(user_agent, client_hints=None):
    client_hints = client_hints or {}
    parse_user_agent = _get_user_agent_parser()
    browser_name = "Unknown"
    device_name = "Unknown device"
    brand_name = "Unknown"
    mobile_model = "Not available"

    if parse_user_agent and user_agent:
        parsed = parse_user_agent(user_agent)

        if parsed.browser and parsed.browser.family and parsed.browser.family != "Other":
            version = parsed.browser.version_string
            browser_name = f"{parsed.browser.family} {version}".strip() if version else parsed.browser.family

        parsed_brand = getattr(parsed.device, "brand", None)
        parsed_model = getattr(parsed.device, "model", None)
        parsed_family = getattr(parsed.device, "family", None)

        if parsed_brand:
            brand_name = parsed_brand

        if parsed_model:
            mobile_model = parsed_model

        if parsed_brand and parsed_model:
            device_name = f"{parsed_brand} {parsed_model}"
        elif parsed_family and parsed_family != "Other":
            device_name = parsed_family
        elif parsed.os and parsed.os.family and parsed.os.family != "Other":
            device_name = f"{parsed.os.family} device"

    ch_model = client_hints.get("sec_ch_ua_model")
    ch_platform = client_hints.get("sec_ch_ua_platform")
    ch_brand = _parse_ch_brand(client_hints.get("sec_ch_ua") or client_hints.get("sec_ch_ua_full_version_list"))

    if ch_brand:
        brand_name = ch_brand

    if ch_model:
        clean_model = ch_model.strip('" ')
        if clean_model:
            mobile_model = clean_model
            device_name = f"{brand_name} {clean_model}".strip()

    if device_name == "Unknown device" and ch_platform:
        device_name = f"{ch_platform.strip('" ')} device"

    return {
        "browser": browser_name,
        "device_name": device_name,
        "brand_name": brand_name,
        "mobile_model": mobile_model,
    }


def _build_login_location_details(ip_address):
    if not ip_address or ip_address == "Unknown":
        return "Unknown location"

    try:
        parsed_ip = ipaddress.ip_address(ip_address)
        if parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_reserved:
            return "Private network"
    except ValueError:
        return "Unknown location"

    try:
        response = requests.get(
            f"https://ipapi.co/{ip_address}/json/",
            headers={"User-Agent": "djFood-login-security/1.0"},
            timeout=3,
        )
        if response.status_code != 200:
            return "Unknown location"

        payload = response.json()
        city = payload.get("city")
        region = payload.get("region")
        country = payload.get("country_name")
        parts = [part for part in [city, region, country] if part]
        return ", ".join(parts) if parts else "Unknown location"
    except Exception:
        return "Unknown location"



@shared_task(bind=True, max_retries=3)
def notify_new_login(self, user_id, ip_address=None, user_agent=None, client_hints=None):
    """
    Fires after every successful login.
    Security alert — lets user know if someone else logged into their account.
 
    ── Why include IP and device info? ──────────────────────────────────────
    If the user didn't log in — they can immediately know something is wrong.
    Same pattern used by Google, GitHub, every serious platform.
    """
    try:
        User = get_user_model()
        user = User.objects.get(pk=user_id)
        user_name = getattr(user, "name", user.email)
 
        login_time = timezone.now().strftime("%d %b %Y at %I:%M %p")
        ip = ip_address or "Unknown"
        device_details = _build_login_device_details(user_agent, client_hints=client_hints)
        location = _build_login_location_details(ip)
 
        frontend_url  = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        support_email = settings.DEFAULT_FROM_EMAIL
 
        content = f"""
            <p style="margin:0 0 16px;font-size:16px;color:#1a1a1a;font-weight:500;">
                Hi {user_name},
            </p>
            <p style="margin:0 0 24px;font-size:15px;color:#4a4a4a;">
                We noticed a new login to your FoodRevolut account.
            </p>
 
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f9f9f9;border-radius:6px;padding:16px;margin:0 0 24px;">
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">Time</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{login_time} (IST)</td>
                </tr>
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">IP address</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{ip}</td>
                </tr>
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">Location</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{location}</td>
                </tr>
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">Device</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{device_details['device_name']}</td>
                </tr>
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">Browser</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{device_details['browser']}</td>
                </tr>
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">Brand</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{device_details['brand_name']}</td>
                </tr>
                <tr>
                    <td style="font-size:14px;color:#6b6b6b;padding:6px 0;">Mobile model</td>
                    <td style="font-size:14px;color:#1a1a1a;text-align:right;">{device_details['mobile_model']}</td>
                </tr>
            </table>
 
            <p style="margin:0 0 16px;font-size:15px;color:#4a4a4a;">
                If this was you, no action is needed.
            </p>
            <p style="margin:0 0 24px;font-size:15px;color:#4a4a4a;">
                If you did not log in, your account may be compromised.
                Please change your password immediately.
            </p>
 
            <table cellpadding="0" cellspacing="0">
                <tr>
                    <td style="background-color:#e85d30;border-radius:6px;">
                        <a href="{frontend_url}/settings/change-password"
                           style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:14px;font-weight:500;text-decoration:none;">
                            Change Password
                        </a>
                    </td>
                </tr>
            </table>
 
            <p style="margin:24px 0 0;font-size:13px;color:#9b9b9b;">
                If you need help, contact us at {support_email}
            </p>
        """
 
        html = wrap_email_html(content, "New Login Detected")
        text = (
            f"New login to your FoodDelivery account\n"
            f"Time: {login_time}\n"
            f"IP: {ip}\n"
            f"Location: {location}\n"
            f"Device: {device_details['device_name']}\n"
            f"Browser: {device_details['browser']}\n"
            f"Brand: {device_details['brand_name']}\n"
            f"Mobile model: {device_details['mobile_model']}\n\n"
            f"If this wasn't you, change your password immediately: {frontend_url}/settings/change-password"
        )
 
        send_html_email(
            to_email  = user.email,
            subject   = "New Login to Your FoodDelivery Account",
            html_body = html,
            text_body = text,
        )
 
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    


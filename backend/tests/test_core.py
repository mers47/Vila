from app.services.normalization import normalize_phone, normalize_handle
from app.services.policy import can_send
from app.services.reply_classifier import classify_reply
from app.services.scoring import score_lead


def test_normalization():
    assert normalize_phone("0912 123 4567") == "+989121234567"
    assert normalize_handle(" @MyShop/ ") == "myshop"


def test_policy_opt_out_blocks():
    assert not can_send("WHATSAPP", "OPTED_OUT").allowed


def test_policy_whatsapp_template_requires_opt_in():
    assert not can_send("WHATSAPP", "UNKNOWN", message_kind="template").allowed
    assert can_send("WHATSAPP", "OPTED_IN", message_kind="template").allowed


def test_policy_whatsapp_free_text_needs_service_window():
    assert not can_send("WHATSAPP", "OPTED_IN", message_kind="text").allowed


def test_reply_classifier():
    assert classify_reply("لطفا لیست قیمت همکاری رو بفرستید") == "PURCHASE_INTENT"
    assert classify_reply("لطفا دیگه پیام ندید") == "OPT_OUT"


def test_scoring():
    result = score_lead(industry_match=True, city_match=True, active_online=True, has_contact=True,
                        has_social=True, product_match=True, suitable_size=True, need_signal=True)
    assert result.score == 100
    assert result.temperature == "HOT"


def test_public_web_rejects_private_ip():
    import asyncio
    import pytest
    from app.services.url_safety import assert_public_url
    with pytest.raises(ValueError):
        asyncio.run(assert_public_url("http://127.0.0.1/internal"))


def test_public_social_link_parsing():
    from app.services.url_safety import social_handle, whatsapp_number
    assert social_handle("https://instagram.com/Example.Shop/") == "Example.Shop"
    assert social_handle("https://t.me/example_channel") == "example_channel"
    assert whatsapp_number("https://wa.me/989121234567") == "+989121234567"


def test_handle_channels_are_not_messaging_channels():
    assert not can_send("INSTAGRAM_HANDLE", "OPTED_IN", message_kind="text").allowed
    assert not can_send("TELEGRAM_HANDLE", "OPTED_IN", message_kind="text", interaction_started=True).allowed


def test_policy_whatsapp_marketing_template_requires_opt_in():
    assert not can_send("WHATSAPP", "UNKNOWN", message_kind="marketing_template").allowed
    assert can_send("WHATSAPP", "OPTED_IN", message_kind="marketing_template").allowed

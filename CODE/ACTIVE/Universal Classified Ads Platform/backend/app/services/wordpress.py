"""Push published classified ads to WordPress as posts via REST API."""
import base64
import logging
import requests
from ..core.config import get_settings

logger = logging.getLogger(__name__)

try:
    import stripe as _stripe
except ImportError:
    _stripe = None


def _auth_header() -> dict:
    settings = get_settings()
    token = base64.b64encode(f"{settings.wp_user}:{settings.wp_app_password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def is_enabled() -> bool:
    settings = get_settings()
    return bool(settings.wp_enabled and settings.wp_site_url and settings.wp_app_password)


def push_ad_to_wp(ad, media_urls: list[str] | None = None) -> dict | None:
    """Create a WP post from a published classified ad. Returns WP post data or None."""
    if not is_enabled():
        logger.info("WP integration disabled, skipping push")
        return None

    settings = get_settings()
    headers = _auth_header()

    # Build HTML content from ad fields
    html_parts = [f"<p>{ad.description}</p>"]
    if ad.price is not None:
        html_parts.append(f"<p><strong>Price:</strong> ${float(ad.price):.2f}</p>")
    if ad.location:
        html_parts.append(f"<p><strong>Location:</strong> {ad.location}</p>")
    if ad.contact_info:
        html_parts.append(f"<p><strong>Contact:</strong> {ad.contact_info}</p>")
    if ad.tags:
        tag_links = ", ".join(
            f'<a href="{settings.wp_site_url}/?s={t.strip()}">{t.strip()}</a>'
            for t in ad.tags.split(",") if t.strip()
        )
        html_parts.append(f"<p><strong>Tags:</strong> {tag_links}</p>")

    # Embed images if available
    if media_urls:
        for url in media_urls:
            html_parts.append(f'<img src="{url}" class="classified-ad-image" style="max-width:100%;height:auto;margin:8px 0" />')

    content = "\n".join(html_parts)

    post_data = {
        "title": ad.title,
        "content": content,
        "status": "publish",
        "slug": f"classified-{ad.id}-{ad.category}",
        "meta": {
            "_classified_ad_id": str(ad.id),
            "_classified_category": ad.category,
            "_classified_price": str(ad.price) if ad.price else "",
            "_classified_location": ad.location,
        },
    }

    if settings.wp_default_category_id:
        post_data["categories"] = [settings.wp_default_category_id]

    url = f"{settings.wp_site_url.rstrip('/')}/wp-json/wp/v2/posts"
    try:
        resp = requests.post(url, headers=headers, json=post_data, timeout=15)
        resp.raise_for_status()
        wp_post = resp.json()
        logger.info(f"Pushed ad {ad.id} to WP as post {wp_post.get('id')}")
        return wp_post
    except Exception as e:
        logger.error(f"Failed to push ad {ad.id} to WP: {e}")
        return None


def delete_wp_post(wp_post_id: int) -> bool:
    """Delete a WP post by ID (when ad is deleted/archived)."""
    if not is_enabled():
        return False
    settings = get_settings()
    headers = _auth_header()
    url = f"{settings.wp_site_url.rstrip('/')}/wp-json/wp/v2/posts/{wp_post_id}"
    try:
        resp = requests.delete(url, headers=headers, params={"force": True}, timeout=10)
        return resp.status_code in (200, 202)
    except Exception as e:
        logger.error(f"Failed to delete WP post {wp_post_id}: {e}")
        return False

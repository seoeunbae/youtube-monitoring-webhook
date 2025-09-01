import xmltodict
import logging

def parse_webhook_data(xml_data):
    """Parses the XML data from the YouTube webhook.

    Args:
        xml_data: The raw XML data from the request.

    Returns:
        A dictionary containing video details if successful, otherwise None.
    """
    if not xml_data:
        logging.warning("POST request received with empty payload.")
        return None
    try:
        data = xmltodict.parse(xml_data)
        entry = data.get('feed', {}).get('entry')
        if not entry:
            logging.warning("No 'entry' found in the XML data.")
            return None

        video_id = entry.get('yt:videoId')
        channel_id = entry.get('yt:channelId')
        title = entry.get('title')
        published = entry.get('published')

        if not all([video_id, channel_id, title, published]):
            logging.warning("Incomplete data in 'entry'.")
            return None

        return {
            "video_id": video_id,
            "channel_id": channel_id,
            "title": title,
            "published": published
        }
    except Exception as e:
        logging.error(f"Error parsing XML: {e}")
        return None

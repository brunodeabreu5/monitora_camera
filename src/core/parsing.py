# Parsing de XML de eventos Hikvision
import xml.etree.ElementTree as ET

from .config import now_str


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def detect_text(root, names):
    wanted = {n.lower() for n in names}
    for elem in root.iter():
        tag = strip_ns(elem.tag).lower()
        if tag in wanted and elem.text and elem.text.strip():
            return elem.text.strip()
    return ""


def parse_event_xml(xml_text: str) -> dict | None:
    xml_text = xml_text.strip()
    if not xml_text:
        return None
    data = {"ts": now_str(), "plate": "", "speed": "", "lane": "", "direction": "", "event_type": "", "raw_xml": xml_text}
    try:
        root = ET.fromstring(xml_text)
        data["event_type"] = detect_text(root, ["eventType", "eventDescription", "eventName", "type", "eventTypeEx", "alarmType", "vehicleDetectType"])
        data["plate"] = detect_text(root, ["licensePlate", "plateNo", "vehiclePlate", "plateNumber", "license", "plate"])
        data["speed"] = detect_text(root, [
            "speed", "vehicleSpeed", "vehicleSpeedValue",
            "speedValue", "vehicleSpeedKmh", "speedKmh", "speedValueKmh",
        ])
        data["lane"] = detect_text(root, ["laneNo", "lane", "driveLane"])
        data["direction"] = detect_text(root, ["direction", "driveDirection", "vehicleDirection"])
        date_part = detect_text(root, ["dateTime", "time", "captureTime", "occurTime"])
        if date_part:
            data["ts"] = date_part
        return data
    except ET.ParseError:
        return None


def looks_like_complete_event_xml(xml_text: str) -> bool:
    xml_text = xml_text.strip()
    if not xml_text or "</" not in xml_text:
        return False
    return (
        xml_text.endswith("</EventNotificationAlert>")
        or xml_text.endswith("</ANPR>")
    )

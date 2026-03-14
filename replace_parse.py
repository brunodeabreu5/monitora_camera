from pathlib import Path
path = Path('hikvision_pro_v42_app.py')
text = path.read_text(encoding='utf-8')
start = text.index('def parse_event_xml')
end = text.index('\n\nclass CameraClient', start)
old = text[start:end]
new = '''def parse_event_xml(xml_text: str) -> dict | None:
    xml_text = xml_text.strip()
    if not xml_text:
        return None
    data = {"ts": now_str(), "plate": "", "speed": "", "lane": "", "direction": "", "event_type": "", "raw_xml": xml_text}
    try:
        root = ET.fromstring(xml_text)
        data["event_type"] = detect_text(root, ["eventType", "eventDescription", "eventName", "type", "eventTypeEx", "alarmType", "vehicleDetectType"])
        data["plate"] = detect_text(root, ["licensePlate", "plateNo", "plateNumber", "license", "plate"])
        data["speed"] = detect_text(root, ["speed", "vehicleSpeed", "vehicleSpeedValue"])
        data["lane"] = detect_text(root, ["laneNo", "lane", "driveLane"])
        data["direction"] = detect_text(root, ["direction", "driveDirection", "vehicleDirection"])
        date_part = detect_text(root, ["dateTime", "time", "captureTime", "occurTime"])
        if date_part:
            data["ts"] = date_part
        return data
    except Exception as exc:
        log_runtime_error("Falha ao interpretar XML de evento", exc)
        return None

'''
if old not in text:
    raise SystemExit('old block not found')
path.write_text(text[:start] + new + text[end:], encoding='utf-8')

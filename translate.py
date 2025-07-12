import pytesseract
from googletrans import Translator
from PIL import ImageGrab
import time
from log_utils import log_error

translator = Translator()

def get_text_from_chat(capture_region, overlay_obj):
    if not capture_region:
        return ""
    try:
        overlay_obj.hide()
        time.sleep(0.08)
        image = ImageGrab.grab(bbox=capture_region)
        overlay_obj.show("reading text...")
        return pytesseract.image_to_string(image, lang='rus+eng')
    except Exception as e:
        log_error(f"OCR error: {e}")
        return ""

def translate_text_google(text):
    try:
        result = translator.translate(text, src='ru', dest='en')
        return result.text
    except Exception as e:
        log_error(f"Translation error: {e}")
        return f"[Translation Error] {e}"

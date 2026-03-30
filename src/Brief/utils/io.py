import base64

def check_file_exists(image_path):
    try:
        with open(image_path, "rb"):
            return True
    except FileNotFoundError:
        return False

# local image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    return image_base64


# 帮我写一个代码，以文本形式读取代码文件
def read_code_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        code_content = file.read()
    return code_content
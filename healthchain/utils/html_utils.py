def clean_html(text):
    """
    Standardize HTML handling across the project
    """
    if not text:
        return ""

    # convert to string
    text = str(text)

    # remove extra spaces
    text = text.strip()

    return text


def normalize_quantity(value):
    """
    Ensure numbers are always integers when possible
    """
    try:
        return int(value)
    except:
        return value
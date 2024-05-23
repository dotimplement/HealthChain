import os
import json
import re
import streamlit as st


st.set_page_config(page_title="HealthChain Json Viewer", layout="wide")


# Function to read JSON files
def read_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def find_matching_files(folder1, folder2):
    pattern_request = re.compile(r"(.*)_request_.*\.json$")
    pattern_response = re.compile(r"(.*)_response_.*\.json$")

    files1 = {
        pattern_request.match(f).group(1): f
        for f in os.listdir(folder1)
        if pattern_request.match(f)
    }
    files2 = {
        pattern_response.match(f).group(1): f
        for f in os.listdir(folder2)
        if pattern_response.match(f)
    }

    matching_uids = set(files1.keys()).intersection(set(files2.keys()))
    return [(files1[uid], files2[uid]) for uid in matching_uids]


# Function to recursively remove empty lists from JSON data
def remove_empty_lists(obj):
    if isinstance(obj, dict):
        return {
            k: remove_empty_lists(v)
            for k, v in obj.items()
            if not (isinstance(v, list) and not v)
        }
    elif isinstance(obj, list):
        return [
            remove_empty_lists(item)
            for item in obj
            if not (isinstance(item, list) and not item)
        ]
    else:
        return obj


# Streamlit app
def main():
    st.title("JSON File Matcher and Viewer")

    # Sidebar for user input and selection
    st.sidebar.title("Settings")
    folder = st.sidebar.text_input("Enter the base path to the folders:")
    folder1 = os.path.join(folder, "requests")
    folder2 = os.path.join(folder, "responses")

    if folder1 and folder2:
        if os.path.isdir(folder1) and os.path.isdir(folder2):
            matching_files = find_matching_files(folder1, folder2)
            st.sidebar.write(f"Found {len(matching_files)} matching files.")

            if matching_files:
                file_selection = st.sidebar.selectbox(
                    "Select a file to view",
                    matching_files,
                    format_func=lambda x: x[0].split("_")[2],
                )

                request_file, response_file = file_selection
                file_path1 = os.path.join(folder1, request_file)
                file_path2 = os.path.join(folder2, response_file)

                data1 = read_json(file_path1)
                data2 = read_json(file_path2)

                data1 = remove_empty_lists(data1)
                data2 = remove_empty_lists(data2)

                st.write(f"### Viewing: {file_selection[0].split('_')[2]}")
                col1, col2 = st.columns([2, 2])  # Adjust column width here

                with st.expander("Request JSON"):
                    st.json(data1)

                text = [
                    f"* {key}: {value}"
                    for card in data2["cards"]
                    for key, value in card.items()
                ]
                markdown_text = "\n".join(text)
                st.info(f"## Server Response: \n {markdown_text}")


if __name__ == "__main__":
    main()

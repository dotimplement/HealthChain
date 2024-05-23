import streamlit as st


def main():
    with open("../node_modules/nes.css/css/nes.css") as f:
        css = f.read()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.title("My Streamlit App")
    st.write("Welcome to my app!")
    st.write("This app generates synthetic health data.")
    st.write(
        "The data is generated using the `EncounterGenerator` class from the `healthchain` package."
    )

    # # Create an instance of the EncounterGenerator class
    # with st.sidebar:
    #     st.write("### Encounter Generator")
    #     st.write("Use the EncounterGenerator to generate synthetic health data.")
    #     st.write("Click the button below to generate a synthetic encounter.")

    # generator = EncounterGenerator()

    # # Generate a synthetic encounter on button click
    # if st.button("Generate Encounter"):
    #     encounter = generator.generate()
    #     st.json(encounter.model_dump_json(exclude_none=True))


if __name__ == "__main__":
    main()

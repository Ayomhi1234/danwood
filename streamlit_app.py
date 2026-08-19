"""
Danwood House Search System
Compatible with the new Danwood scraped JSON database.

Database table:
    danwood_houses

Record types:
    house
    configurator
    garage
    carport
    category
    404
"""

import os
import mysql.connector
import pandas as pd
import streamlit as st

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Danwood Hausprojekte",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        padding: 0;
    }

    .house-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }

    .house-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    .header-box {
        background: linear-gradient(
            135deg,
            #3b82f6,
            #1e40af
        );

        color: white;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 25px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_db_connection():

    try:

        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "danwood")
        )

        return connection

    except Exception as error:

        st.error(
            f"Database connection failed: {error}"
        )

        return None


# ============================================================
# LOAD HOUSES
# ============================================================

@st.cache_data(ttl=300)
def get_houses():

    connection = get_db_connection()

    if connection is None:
        return pd.DataFrame()

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                db_id,
                source_id,
                name,
                url,
                category,
                square_meters,
                rooms,
                bathrooms,
                floors,
                description,
                record_type,
                imported_at

            FROM danwood_houses

            WHERE record_type = 'house'

            ORDER BY name
            """
        )

        data = cursor.fetchall()

        cursor.close()

        return pd.DataFrame(data)

    except Exception as error:

        st.error(
            f"Error loading houses: {error}"
        )

        return pd.DataFrame()


# ============================================================
# LOAD ALL RECORD TYPES
# ============================================================

@st.cache_data(ttl=300)
def get_record_summary():

    connection = get_db_connection()

    if connection is None:
        return pd.DataFrame()

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                record_type,
                COUNT(*) AS total

            FROM danwood_houses

            GROUP BY record_type

            ORDER BY record_type
            """
        )

        data = cursor.fetchall()

        cursor.close()

        return pd.DataFrame(data)

    except Exception as error:

        st.error(
            f"Error loading record summary: {error}"
        )

        return pd.DataFrame()


# ============================================================
# LOAD CATEGORIES
# ============================================================

@st.cache_data(ttl=300)
def get_categories():

    connection = get_db_connection()

    if connection is None:
        return []

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT DISTINCT category

            FROM danwood_houses

            WHERE record_type = 'house'

            AND category IS NOT NULL

            AND category != ''

            ORDER BY category
            """
        )

        categories = [
            row[0]
            for row in cursor.fetchall()
        ]

        cursor.close()

        return categories

    except Exception as error:

        st.error(
            f"Error loading categories: {error}"
        )

        return []


# ============================================================
# HOUSE DETAILS
# ============================================================

def get_house_details(db_id):

    connection = get_db_connection()

    if connection is None:
        return None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *

            FROM danwood_houses

            WHERE db_id = %s

            LIMIT 1
            """,
            (db_id,)
        )

        house = cursor.fetchone()

        cursor.close()

        return house

    except Exception as error:

        st.error(
            f"Error loading house details: {error}"
        )

        return None


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="header-box">

            <h1>🏠 Danwood Hausprojekte</h1>

            <p>
            Finden Sie Ihr passendes Danwood-Haus
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    houses = get_houses()

    summary = get_record_summary()

    categories = get_categories()

    if houses.empty:

        st.warning(
            """
            Keine Häuser gefunden.

            Stellen Sie sicher, dass:

            1. MySQL läuft.
            2. Ihre .env korrekt ist.
            3. import_danwood_db.py ausgeführt wurde.
            """
        )

        return


    # --------------------------------------------------------
    # DATABASE OVERVIEW
    # --------------------------------------------------------

    st.subheader("Datenbankübersicht")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Häuser",
            len(houses)
        )

    with col2:

        st.metric(
            "Kategorien",
            houses["category"].nunique()
        )

    with col3:

        average_area = houses[
            "square_meters"
        ].mean()

        st.metric(
            "Ø Fläche",
            f"{average_area:.1f} m²"
        )

    with col4:

        average_rooms = houses[
            "rooms"
        ].mean()

        st.metric(
            "Ø Zimmer",
            f"{average_rooms:.1f}"
        )


    # --------------------------------------------------------
    # RECORD SUMMARY
    # --------------------------------------------------------

    with st.expander(
        "Datenbank-Aufschlüsselung"
    ):

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True
        )


    st.divider()


    # ========================================================
    # SIDEBAR FILTERS
    # ========================================================

    st.sidebar.header(
        "Filter"
    )


    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search_term = st.sidebar.text_input(
        "Haus suchen",
        placeholder="z.B. Perfect 120"
    )


    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    selected_categories = st.sidebar.multiselect(
        "Haustyp",
        options=categories
    )


    # --------------------------------------------------------
    # AREA
    # --------------------------------------------------------

    valid_area = houses[
        houses["square_meters"].notna()
    ]["square_meters"]


    if not valid_area.empty:

        minimum_area = int(
            valid_area.min()
        )

        maximum_area = int(
            valid_area.max()
        )

    else:

        minimum_area = 0
        maximum_area = 500


    min_sqm, max_sqm = st.sidebar.slider(
        "Wohnfläche (m²)",
        min_value=minimum_area,
        max_value=maximum_area,
        value=(
            minimum_area,
            maximum_area
        )
    )


    # --------------------------------------------------------
    # ROOMS
    # --------------------------------------------------------

    valid_rooms = houses[
        houses["rooms"].notna()
    ]["rooms"]


    if not valid_rooms.empty:

        min_room_value = int(
            valid_rooms.min()
        )

        max_room_value = int(
            valid_rooms.max()
        )

    else:

        min_room_value = 0
        max_room_value = 10


    min_rooms, max_rooms = st.sidebar.slider(
        "Zimmer",
        min_value=min_room_value,
        max_value=max_room_value,
        value=(
            min_room_value,
            max_room_value
        )
    )


    # --------------------------------------------------------
    # FLOOR
    # --------------------------------------------------------

    floor_options = sorted(
        houses["floors"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_floors = st.sidebar.multiselect(
        "Geschosse",
        options=floor_options
    )


    # ========================================================
    # APPLY FILTERS
    # ========================================================

    filtered = houses.copy()


    # Search

    if search_term:

        search_text = search_term.strip()

        filtered = filtered[
            filtered["name"].fillna("").str.contains(
                search_text,
                case=False,
                regex=False
            )
        ]


    # Category

    if selected_categories:

        filtered = filtered[
            filtered["category"].isin(
                selected_categories
            )
        ]


    # Area

    filtered = filtered[
        filtered["square_meters"].between(
            min_sqm,
            max_sqm,
            inclusive="both"
        )
        |
        filtered["square_meters"].isna()
    ]


    # Rooms

    filtered = filtered[
        filtered["rooms"].between(
            min_rooms,
            max_rooms,
            inclusive="both"
        )
        |
        filtered["rooms"].isna()
    ]


    # Floors

    if selected_floors:

        filtered = filtered[
            filtered["floors"]
            .astype(str)
            .isin(selected_floors)
        ]


    # ========================================================
    # RESULTS
    # ========================================================

    st.subheader(
        f"{len(filtered)} Häuser gefunden"
    )


    if filtered.empty:

        st.info(
            "Keine Häuser entsprechen Ihren Filtern."
        )

        return


    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    sort_option = st.selectbox(
        "Sortieren nach",
        [
            "Name",
            "Wohnfläche aufsteigend",
            "Wohnfläche absteigend",
            "Zimmer aufsteigend",
            "Zimmer absteigend"
        ]
    )


    if sort_option == "Name":

        filtered = filtered.sort_values(
            "name"
        )

    elif sort_option == "Wohnfläche aufsteigend":

        filtered = filtered.sort_values(
            "square_meters",
            na_position="last"
        )

    elif sort_option == "Wohnfläche absteigend":

        filtered = filtered.sort_values(
            "square_meters",
            ascending=False,
            na_position="last"
        )

    elif sort_option == "Zimmer aufsteigend":

        filtered = filtered.sort_values(
            "rooms",
            na_position="last"
        )

    elif sort_option == "Zimmer absteigend":

        filtered = filtered.sort_values(
            "rooms",
            ascending=False,
            na_position="last"
        )


    # ========================================================
    # HOUSE GRID
    # ========================================================

    columns = st.columns(3)


    for index, (_, house) in enumerate(
        filtered.iterrows()
    ):

        with columns[index % 3]:

            with st.container(
                border=True
            ):

                # --------------------------------------------
                # HOUSE NAME
                # --------------------------------------------

                st.subheader(
                    house["name"]
                )


                # --------------------------------------------
                # CATEGORY
                # --------------------------------------------

                category = (
                    house["category"]
                    if pd.notna(house["category"])
                    else "Unknown"
                )

                st.caption(
                    f"Haustyp: {category}"
                )


                # --------------------------------------------
                # SPECS
                # --------------------------------------------

                col1, col2, col3 = st.columns(3)


                with col1:

                    sqm = house["square_meters"]

                    if pd.notna(sqm):

                        st.metric(
                            "m²",
                            f"{sqm:.2f}"
                        )

                    else:

                        st.metric(
                            "m²",
                            "-"
                        )


                with col2:

                    rooms = house["rooms"]

                    if pd.notna(rooms):

                        st.metric(
                            "Zimmer",
                            int(rooms)
                        )

                    else:

                        st.metric(
                            "Zimmer",
                            "-"
                        )


                with col3:

                    bathrooms = house["bathrooms"]

                    if pd.notna(bathrooms):

                        st.metric(
                            "Bäder",
                            int(bathrooms)
                        )

                    else:

                        st.metric(
                            "Bäder",
                            "-"
                        )


                # --------------------------------------------
                # DESCRIPTION
                # --------------------------------------------

                description = house[
                    "description"
                ]

                if pd.notna(description):

                    description = str(
                        description
                    )

                    if len(description) > 180:

                        description = (
                            description[:180]
                            + "..."
                        )

                    st.write(
                        description
                    )


                # --------------------------------------------
                # FLOOR
                # --------------------------------------------

                if pd.notna(
                    house["floors"]
                ):

                    st.caption(
                        f"Geschosse: {house['floors']}"
                    )


                # --------------------------------------------
                # OPEN DETAILS
                # --------------------------------------------

                if st.button(
                    "Details ansehen",
                    key=f"details_{house['db_id']}",
                    use_container_width=True
                ):

                    st.session_state[
                        "selected_house_id"
                    ] = int(
                        house["db_id"]
                    )

                    st.rerun()


                # --------------------------------------------
                # ORIGINAL DANWOOD PAGE
                # --------------------------------------------

                if pd.notna(house["url"]):

                    st.link_button(
                        "Danwood-Seite öffnen",
                        house["url"],
                        use_container_width=True
                    )


    # ========================================================
    # HOUSE DETAILS
    # ========================================================

    selected_id = st.session_state.get(
        "selected_house_id"
    )


    if selected_id:

        st.divider()

        house = get_house_details(
            selected_id
        )


        if house:

            st.header(
                house["name"]
            )


            col1, col2 = st.columns(2)


            with col1:

                st.write(
                    f"**Haustyp:** "
                    f"{house['category'] or '-'}"
                )

                st.write(
                    f"**Wohnfläche:** "
                    f"{house['square_meters'] or '-'} m²"
                )

                st.write(
                    f"**Zimmer:** "
                    f"{house['rooms'] or '-'}"
                )


            with col2:

                st.write(
                    f"**Badezimmer:** "
                    f"{house['bathrooms'] or '-'}"
                )

                st.write(
                    f"**Geschosse:** "
                    f"{house['floors'] or '-'}"
                )

                st.write(
                    f"**Datensatztyp:** "
                    f"{house['record_type']}"
                )


            st.subheader(
                "Beschreibung"
            )


            if house["description"]:

                st.write(
                    house["description"]
                )


            if house["url"]:

                st.link_button(
                    "Original Danwood-Seite",
                    house["url"]
                )


            if st.button(
                "Schließen"
            ):

                del st.session_state[
                    "selected_house_id"
                ]

                st.rerun()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
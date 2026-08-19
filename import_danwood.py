import os
import json
from decimal import Decimal

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

JSON_FILE = "danwood_complete_database_260_houses.json"
DATABASE_NAME = os.getenv("DB_NAME", "danwood_houses")
TABLE_NAME = "danwood_houses"

load_dotenv()


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


# ============================================================
# LOAD JSON
# ============================================================

def load_json():

    if not os.path.exists(JSON_FILE):
        raise FileNotFoundError(
            f"Could not find '{JSON_FILE}'. "
            "Make sure the JSON file is in the same folder."
        )

    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "The JSON file must contain a list of records."
        )

    print(f"JSON records found: {len(data)}")

    return data


# ============================================================
# CLEAN VALUES
# ============================================================

def clean_text(value):

    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def clean_int(value):

    if value is None or value == "":
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def clean_decimal(value):

    if value is None or value == "":
        return None

    try:
        return Decimal(str(value))
    except Exception:
        return None


# ============================================================
# DETERMINE RECORD TYPE
# ============================================================

def classify_record(record):

    name = str(
        record.get("name") or ""
    ).lower()

    url = str(
        record.get("url") or ""
    ).lower()

    # 404 pages
    if "fehler 404" in name or "404" in url:
        return "404"

    # Configurator pages
    if (
        "hauskonfigurator" in name
        or "/hauskonfigurator" in url
    ):
        return "configurator"

    # Garage / carport pages
    if "/garagen-und-carports/" in url:

        if "carport" in name:
            return "carport"

        return "garage"

    # Category pages
    if (
        record.get("square_meters") is None
        and record.get("rooms") is None
        and record.get("bathrooms") is None
        and record.get("floors") is None
    ):
        return "category"

    # Actual house
    return "house"


# ============================================================
# CONNECT TO MYSQL SERVER
# ============================================================

def connect_to_server():

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )


# ============================================================
# CREATE DATABASE
# ============================================================

def create_database():

    connection = connect_to_server()
    cursor = connection.cursor()

    cursor.execute(
        f"""
        CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}`
        CHARACTER SET utf8mb4
        COLLATE utf8mb4_unicode_ci
        """
    )

    connection.commit()

    cursor.close()
    connection.close()

    print(
        f"Database '{DATABASE_NAME}' is ready."
    )


# ============================================================
# CONNECT TO DATABASE
# ============================================================

def connect_to_database():

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DATABASE_NAME
    )


# ============================================================
# CREATE NEW IMPORT TABLE
# ============================================================

def create_import_table(connection):

    cursor = connection.cursor()

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{TABLE_NAME}` (

            db_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

            source_id VARCHAR(255),

            name VARCHAR(500),

            url VARCHAR(1000) NOT NULL,

            category VARCHAR(100),

            square_meters DECIMAL(10,2),

            rooms INT,

            bathrooms INT,

            floors VARCHAR(20),

            description LONGTEXT,

            record_type ENUM(
                'house',
                'configurator',
                'garage',
                'carport',
                'category',
                '404'
            ) NOT NULL DEFAULT 'house',

            imported_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (db_id),

            UNIQUE KEY unique_url (url(500)),

            INDEX idx_category (category),

            INDEX idx_record_type (record_type),

            INDEX idx_square_meters (square_meters),

            INDEX idx_rooms (rooms),

            INDEX idx_bathrooms (bathrooms),

            INDEX idx_floors (floors)

        )
        ENGINE=InnoDB
        DEFAULT CHARSET=utf8mb4
        COLLATE=utf8mb4_unicode_ci
        """
    )

    connection.commit()

    cursor.close()

    print(
        f"Table '{TABLE_NAME}' is ready."
    )


# ============================================================
# IMPORT JSON RECORDS
# ============================================================

def import_records(connection, records):

    cursor = connection.cursor()

    query = f"""
        INSERT INTO `{TABLE_NAME}` (

            source_id,
            name,
            url,
            category,
            square_meters,
            rooms,
            bathrooms,
            floors,
            description,
            record_type

        )

        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )

        ON DUPLICATE KEY UPDATE

            source_id = VALUES(source_id),

            name = VALUES(name),

            category = VALUES(category),

            square_meters = VALUES(square_meters),

            rooms = VALUES(rooms),

            bathrooms = VALUES(bathrooms),

            floors = VALUES(floors),

            description = VALUES(description),

            record_type = VALUES(record_type)
    """

    processed = 0
    skipped = 0

    for record in records:

        url = clean_text(
            record.get("url")
        )

        if not url:
            skipped += 1
            continue

        record_type = classify_record(record)

        values = (
            clean_text(record.get("id")),
            clean_text(record.get("name")),
            url,
            clean_text(record.get("category")),
            clean_decimal(record.get("square_meters")),
            clean_int(record.get("rooms")),
            clean_int(record.get("bathrooms")),
            clean_text(record.get("floors")),
            clean_text(record.get("description")),
            record_type
        )

        cursor.execute(query, values)

        processed += 1

    connection.commit()

    cursor.close()

    print(f"Records processed: {processed}")
    print(f"Records skipped: {skipped}")


# ============================================================
# DATABASE SUMMARY
# ============================================================

def print_summary(connection):

    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        f"""
        SELECT
            record_type,
            COUNT(*) AS total

        FROM `{TABLE_NAME}`

        GROUP BY record_type

        ORDER BY record_type
        """
    )

    rows = cursor.fetchall()

    print("\n==========================================")
    print("DANWOOD DATABASE SUMMARY")
    print("==========================================")

    total = 0

    for row in rows:

        print(
            f"{row['record_type']:15} : {row['total']}"
        )

        total += row["total"]

    print("------------------------------------------")
    print(f"{'TOTAL':15} : {total}")
    print("==========================================")

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM `{TABLE_NAME}`
        WHERE record_type = 'house'
        """
    )

    actual_houses = cursor.fetchone()["total"]

    print(
        f"\nActual house records: {actual_houses}"
    )

    cursor.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print("\nStarting Danwood database import...\n")

    records = load_json()

    create_database()

    connection = connect_to_database()

    try:

        if not connection.is_connected():
            raise Error(
                "Could not connect to MySQL."
            )

        print("MySQL connection successful.")

        create_import_table(connection)

        print("\nImporting records...")

        import_records(
            connection,
            records
        )

        print_summary(
            connection
        )

        print(
            "\nDanwood database import completed successfully."
        )

    finally:

        if connection.is_connected():

            connection.close()

            print(
                "MySQL connection closed."
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except FileNotFoundError as error:

        print(f"\nFILE ERROR: {error}")

    except Error as error:

        print(f"\nMYSQL ERROR: {error}")

    except Exception as error:

        print(f"\nERROR: {error}")
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

SET_NUM = "76344-1"

BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = BASE_DIR / "cache" / f"{SET_NUM}.json"


def load_inventory():
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"Cache file not found:\n{CACHE_FILE}\n"
            "Download the inventory first."
        )

    with open(CACHE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("results", [])


def get_lego_colour(colour):
    external_ids = colour.get("external_ids") or {}
    lego_colour = external_ids.get("LEGO") or {}

    lego_ids = lego_colour.get("ext_ids") or []
    lego_descriptions = lego_colour.get("ext_descrs") or []

    lego_colour_id = "Unknown"
    lego_colour_name = colour.get("name", "Unknown")

    if lego_ids:
        lego_colour_id = lego_ids[0]

    if lego_descriptions:
        first_description = lego_descriptions[0]

        if isinstance(first_description, list) and first_description:
            lego_colour_name = first_description[0]

        elif isinstance(first_description, str):
            lego_colour_name = first_description

    return lego_colour_name, lego_colour_id


def get_image_element_id(part):
    part_img_url = str(part.get("part_img_url", "")).strip()

    if not part_img_url:
        return ""

    parsed_url = urlparse(part_img_url)
    filename = Path(parsed_url.path).name

    if not filename:
        return ""

    return Path(filename).stem


def copy_to_clipboard(text):
    try:
        subprocess.run(
            ["pbcopy"],
            input=str(text),
            text=True,
            check=True,
        )
        return True

    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def find_element(inventory, element_id):
    matches = []
    element_id = str(element_id).strip()

    for entry in inventory:
        part = entry.get("part") or {}
        colour = entry.get("color") or {}

        cached_element_id = str(entry.get("element_id", "")).strip()
        image_element_id = get_image_element_id(part)

        possible_element_ids = {
            value
            for value in (cached_element_id, image_element_id)
            if value
        }

        if element_id not in possible_element_ids:
            continue

        lego_colour_name, lego_colour_id = get_lego_colour(colour)

        matches.append(
            {
                "searched_element_id": element_id,
                "cached_element_id": cached_element_id or "Unknown",
                "image_element_id": image_element_id or "Unknown",
                "part_num": part.get("part_num", "Unknown"),
                "part_name": part.get("name", "Unknown"),
                "lego_colour_name": lego_colour_name,
                "lego_colour_id": lego_colour_id,
                "rebrickable_colour_name": colour.get("name", "Unknown"),
                "rebrickable_colour_id": colour.get("id", "Unknown"),
                "rgb": colour.get("rgb", "Unknown"),
                "quantity": entry.get("quantity", "Unknown"),
                "is_spare": entry.get("is_spare", False),
            }
        )

    return matches


def print_result(result):
    part_code = result["part_num"]
    colour_code = result["lego_colour_id"]

    copied = copy_to_clipboard(part_code)

    print()
    print(f"Part code:    {part_code}")
    print(f"Colour code:  {colour_code}")
    print()
    print(f"Part name:    {result['part_name']}")
    print(f"Colour:       {result['lego_colour_name']}")

    if copied:
        print("Part code copied to clipboard.")
    else:
        print("Could not copy the part code to the clipboard.")

    print()


def main():
    try:
        inventory = load_inventory()

    except FileNotFoundError as error:
        print(error)
        return

    except json.JSONDecodeError:
        print(f"The cache file is not valid JSON:\n{CACHE_FILE}")
        return

    print(f"LEGO parts lookup — set {SET_NUM}")
    print(f"Loaded {len(inventory)} cached inventory entries.")
    print("Paste an element ID from the instruction manual.")
    print("The part code will be copied automatically.")
    print("Type q to quit.")
    print()

    while True:
        try:
            element_id = input("Element ID: ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if element_id.lower() in {"q", "quit", "exit"}:
            print("Goodbye.")
            break

        if not element_id:
            continue

        if not element_id.isdigit():
            print("Please enter a numerical LEGO element ID.")
            continue

        matches = find_element(inventory, element_id)

        if not matches:
            print(
                f"No match found for element ID {element_id} "
                f"in set {SET_NUM}."
            )
            continue

        for result in matches:
            print_result(result)


if __name__ == "__main__":
    main()
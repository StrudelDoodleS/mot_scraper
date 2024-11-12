import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from typing import List, Dict
import numpy as np


BASE_URL = "https://www.gov.uk/guidance/mot-inspection-manual-for-private-passenger-and-light-commercial-vehicles"


def get_section_urls(url: str = BASE_URL) -> List[str]:
    """
    Retrieve section URLs from the MOT inspection manual base page.

    Args:
        url (str): The base URL of the MOT inspection manual. Defaults to BASE_URL.

    Returns:
        List[str]: A list of URLs for each section in the manual.
    """
    base_html = requests.get(url).text
    base_soup = BeautifulSoup(base_html, "html.parser")
    all_links = base_soup.find_all("li", class_="gem-c-document-list__item")
    links = [
        "/".join([BASE_URL, link.div.a["href"].split("/")[-1]])
        for link in all_links
        if link.div.text.strip()[0].isdigit()
    ]

    return links


def get_dropdowns(url: str) -> List[BeautifulSoup]:
    """
    Retrieve dropdown sections from a given MOT inspection manual section page.

    Args:
        url (str): The URL of a specific section in the MOT inspection manual.

    Returns:
        List[BeautifulSoup]: A list of BeautifulSoup objects representing each dropdown section.
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("div", class_="govuk-accordion__section")


def generate_mot_table(dropdowns: List[BeautifulSoup]) -> pd.DataFrame:
    """
    Generate a DataFrame representing the MOT inspection table structure from dropdown sections.

    Args:
        dropdowns (List[BeautifulSoup]): A list of BeautifulSoup objects, each representing a section of
                                         the MOT inspection manual containing table data.

    Returns:
        pd.DataFrame: A concatenated DataFrame of all tables found in the dropdown sections. Each row
                      contains structured data including section names, component names, reference codes,
                      and categories extracted from tables within the dropdown sections.

    Notes:
        - The function filters out any sections without tables or any tables without relevant data.
        - Ensures headings `h1`, `h2`, and `h3` are used consistently, with `h3` validated for
          expected "x.y." format using regex. If `h3` doesn't match the section index, it is ignored.
        - Handles multi-line table entries with embedded codes by parsing text split by line breaks.
    """
    sub_section_dfs: Dict[int, List[pd.DataFrame]] = {}
    h3_pattern = re.compile(r"^(\d+)\.(\d+)\..*")

    for idx, sub_section in enumerate(dropdowns):
        tables = sub_section.find_all("table")
        sub_section_dfs[idx + 1] = []

        for table in tables:
            h1 = table.find_previous("h1")
            h2 = table.find_previous("h2")
            h3 = table.find_previous("h3")

            # Validate h3 format and section number
            if h3:
                match = h3_pattern.match(h3.text)
                if match and int(match.group(2)) == idx + 1:
                    h3_name = h3.text.strip()
                else:
                    h3 = None
                    h3_name = ""
            else:
                h3_name = ""

            h1_name = h1.text.strip() if h1 else ""
            h2_name = h2.text.strip() if h2 else ""

            # Get section ID from the appropriate heading
            section_heading = h3 if h3 else h2
            section_id = (
                section_heading["id"].replace("section-", "").replace("-", ".")
                if section_heading and section_heading.get("id")
                else ""
            )

            # Define columns based on table headers
            columns = [
                "section_name",
                "subsection_name",
                "component_name",
                "full_reference_code",
            ] + [th.text.strip() for th in table.find_all("th")]
            rows = []

            for tr in table.find_all("tr")[1:]:
                if tr.find_previous("th").text not in ["Category", "Defect"]:
                    continue
                cells = tr.find_all("td")
                if len(cells) == 2:
                    defect_cell = cells[0]
                    category_cell = cells[1]
                    categories = category_cell.get_text(
                        separator="|||", strip=True
                    ).split("|||")
                    category = categories[0].strip()
                    main_text = defect_cell.get_text(separator="|||", strip=True)
                    parts = main_text.split("|||")

                    # Handling multi-line table entries with embedded codes
                    if len(parts) > 1:
                        main_code = parts[0].split()[0].strip("()")
                        parent_desc = parts[0].split(")", 1)[1].strip().rstrip(":")
                        for i, part in enumerate(parts[1:]):
                            if part.strip():
                                if "(" in part and ")" in part:
                                    sub_code = part[
                                        part.find("(") + 1 : part.find(")")
                                    ].strip()
                                    sub_desc = part[part.find(")") + 1 :].strip()
                                    full_section = (
                                        f"{section_id} ({main_code}) ({sub_code})"
                                    )
                                    full_desc = f"({main_code}) ({sub_code}) {parent_desc} - {sub_desc}"
                                    sub_category = (
                                        categories[i]
                                        if i < len(categories)
                                        else categories[0]
                                    )
                                    rows.append(
                                        [
                                            h1_name,
                                            h2_name,
                                            h3_name,
                                            full_section,
                                            full_desc,
                                            sub_category.strip(),
                                        ]
                                    )
                    else:
                        defect_code = defect_cell.text.strip().split()[0].strip("()")
                        full_section = f"{section_id} ({defect_code})"
                        rows.append(
                            [
                                h1_name,
                                h2_name,
                                h3_name,
                                full_section,
                                defect_cell.text.strip(),
                                category,
                            ]
                        )

            if rows:
                df = pd.DataFrame(rows, columns=columns)
                sub_section_dfs[idx + 1].append(df)

        if sub_section_dfs[idx + 1]:
            sub_section_dfs[idx + 1] = pd.concat(
                sub_section_dfs[idx + 1], ignore_index=True
            )

    # Concatenate non-empty lists of DataFrames
    final_df = pd.concat([v for v in sub_section_dfs.values() if len(v)>0], ignore_index=True).reset_index(drop=True)
    #Tidying up sort of.. to lazy to do this in the loop. Looks cleaner here IMO
    final_df['section_number'] = final_df.section_name.str.split('.').str[0].str.rstrip('.')
    final_df['section_name'] = final_df.section_name.str.split(' ').str[1:].str.join(' ')
    
    final_df['subsection_number'] = final_df.subsection_name.str.split(' ').str[0].str.rstrip('.').str[-1]
    final_df['subsection_name'] = final_df.subsection_name.str.split(' ').str[1:].str.join(' ')
    
    final_df['component_number'] = final_df.component_name.str.split('.').str[0].str.rstrip('.').str[-1]
    final_df['component_name'] = final_df.component_name.str.split(' ').str[1:].str.join(' ')

    final_df['type_ref'] = final_df['Defect'].str.split(' ').str[0].str.strip('()')
    final_df['sub_type_ref'] = np.where(final_df.full_reference_code.str.split(' ').apply(len).eq(3), final_df.full_reference_code.str.split(' ').str[-1].str.strip('()'),"")
    col_order = ['section_name','section_number','subsection_name','subsection_number','component_name','component_number','type_ref','sub_type_ref','full_reference_code','Defect','Category'] 
    
    return final_df[col_order]










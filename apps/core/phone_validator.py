import re
from typing import Dict, Tuple, Optional

# Country-specific phone number validation rules
PHONE_VALIDATION_RULES: Dict[str, Dict[str, any]] = {
    "+1": {  # USA, Canada
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[2-9]\d{9}$",
        "description": "10 digits starting with 2-9",
        "countries": ["USA", "Canada"]
    },
    "+7": {  # Russia, Kazakhstan
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[0-9]{10}$",
        "description": "10 digits",
        "countries": ["Russia", "Kazakhstan"]
    },
    "+20": {  # Egypt
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[0-9]{10}$",
        "description": "10 digits",
        "countries": ["Egypt"]
    },
    "+27": {  # South Africa
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[0-9]{9}$",
        "description": "9 digits",
        "countries": ["South Africa"]
    },
    "+30": {  # Greece
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[0-9]{10}$",
        "description": "10 digits",
        "countries": ["Greece"]
    },
    "+31": {  # Netherlands
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[0-9]{9}$",
        "description": "9 digits",
        "countries": ["Netherlands"]
    },
    "+32": {  # Belgium
        "min_length": 8,
        "max_length": 9,
        "pattern": r"^[0-9]{8,9}$",
        "description": "8 or 9 digits",
        "countries": ["Belgium"]
    },
    "+33": {  # France
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[0-9]{9}$",
        "description": "9 digits",
        "countries": ["France"]
    },
    "+34": {  # Spain
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[6789]\d{8}$",
        "description": "9 digits starting with 6, 7, 8, or 9",
        "countries": ["Spain"]
    },
    "+36": {  # Hungary
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[0-9]{9}$",
        "description": "9 digits",
        "countries": ["Hungary"]
    },
    "+39": {  # Italy
        "min_length": 9,
        "max_length": 10,
        "pattern": r"^3\d{8,9}$",
        "description": "9-10 digits, mobile starts with 3",
        "countries": ["Italy"]
    },
    "+40": {  # Romania
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7\d{8}$",
        "description": "9 digits, mobile starts with 7",
        "countries": ["Romania"]
    },
    "+41": {  # Switzerland
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[0-9]{8}$",
        "description": "9 digits, mobile starts with 7",
        "countries": ["Switzerland"]
    },
    "+43": {  # Austria
        "min_length": 10,
        "max_length": 11,
        "pattern": r"^6[0-9]{9,10}$",
        "description": "10-11 digits, mobile starts with 6",
        "countries": ["Austria"]
    },
    "+44": {  # United Kingdom
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^7[0-9]{9}$",
        "description": "10 digits, mobile starts with 7",
        "countries": ["United Kingdom"]
    },
    "+45": {  # Denmark
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[0-9]{8}$",
        "description": "8 digits",
        "countries": ["Denmark"]
    },
    "+46": {  # Sweden
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[0-9]{8}$",
        "description": "9 digits, mobile starts with 7",
        "countries": ["Sweden"]
    },
    "+47": {  # Norway
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[49]\d{7}$",
        "description": "8 digits, mobile starts with 4 or 9",
        "countries": ["Norway"]
    },
    "+48": {  # Poland
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[456789]\d{8}$",
        "description": "9 digits",
        "countries": ["Poland"]
    },
    "+49": {  # Germany
        "min_length": 10,
        "max_length": 11,
        "pattern": r"^1[567]\d{8,9}$",
        "description": "10-11 digits, mobile starts with 15, 16, or 17",
        "countries": ["Germany"]
    },
    "+51": {  # Peru
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Peru"]
    },
    "+52": {  # Mexico
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[0-9]{10}$",
        "description": "10 digits",
        "countries": ["Mexico"]
    },
    "+53": {  # Cuba
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^5\d{7}$",
        "description": "8 digits, mobile starts with 5",
        "countries": ["Cuba"]
    },
    "+54": {  # Argentina
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[0-9]{10}$",
        "description": "10 digits (without the 9 prefix)",
        "countries": ["Argentina"]
    },
    "+55": {  # Brazil
        "min_length": 11,
        "max_length": 11,
        "pattern": r"^[0-9]{11}$",
        "description": "11 digits",
        "countries": ["Brazil"]
    },
    "+56": {  # Chile
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[0-9]{9}$",
        "description": "9 digits",
        "countries": ["Chile"]
    },
    "+57": {  # Colombia
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^3\d{9}$",
        "description": "10 digits, mobile starts with 3",
        "countries": ["Colombia"]
    },
    "+58": {  # Venezuela
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^4\d{9}$",
        "description": "10 digits, mobile starts with 4",
        "countries": ["Venezuela"]
    },
    "+60": {  # Malaysia
        "min_length": 9,
        "max_length": 10,
        "pattern": r"^1\d{8,9}$",
        "description": "9-10 digits, mobile starts with 1",
        "countries": ["Malaysia"]
    },
    "+61": {  # Australia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^4\d{8}$",
        "description": "9 digits, mobile starts with 4",
        "countries": ["Australia"]
    },
    "+62": {  # Indonesia
        "min_length": 10,
        "max_length": 12,
        "pattern": r"^8\d{9,11}$",
        "description": "10-12 digits, mobile starts with 8",
        "countries": ["Indonesia"]
    },
    "+63": {  # Philippines
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^9\d{9}$",
        "description": "10 digits, mobile starts with 9",
        "countries": ["Philippines"]
    },
    "+64": {  # New Zealand
        "min_length": 8,
        "max_length": 9,
        "pattern": r"^2\d{7,8}$",
        "description": "8-9 digits, mobile starts with 2",
        "countries": ["New Zealand"]
    },
    "+65": {  # Singapore
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[89]\d{7}$",
        "description": "8 digits, mobile starts with 8 or 9",
        "countries": ["Singapore"]
    },
    "+66": {  # Thailand
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[689]\d{8}$",
        "description": "9 digits, mobile starts with 6, 8, or 9",
        "countries": ["Thailand"]
    },
    "+81": {  # Japan
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[789]0\d{8}$",
        "description": "10 digits, mobile starts with 70, 80, or 90",
        "countries": ["Japan"]
    },
    "+82": {  # South Korea
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^1[0-9]{9}$",
        "description": "10 digits, mobile starts with 1",
        "countries": ["South Korea"]
    },
    "+84": {  # Vietnam
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[389]\d{8}$",
        "description": "9 digits, mobile starts with 3, 8, or 9",
        "countries": ["Vietnam"]
    },
    "+86": {  # China
        "min_length": 11,
        "max_length": 11,
        "pattern": r"^1[3-9]\d{9}$",
        "description": "11 digits, mobile starts with 1[3-9]",
        "countries": ["China"]
    },
    "+90": {  # Turkey
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^5\d{9}$",
        "description": "10 digits, mobile starts with 5",
        "countries": ["Turkey"]
    },
    "+91": {  # India
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[6-9]\d{9}$",
        "description": "10 digits starting with 6-9",
        "countries": ["India"]
    },
    "+92": {  # Pakistan
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^3\d{9}$",
        "description": "10 digits, mobile starts with 3",
        "countries": ["Pakistan"]
    },
    "+93": {  # Afghanistan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7\d{8}$",
        "description": "9 digits, mobile starts with 7",
        "countries": ["Afghanistan"]
    },
    "+94": {  # Sri Lanka
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7\d{8}$",
        "description": "9 digits, mobile starts with 7",
        "countries": ["Sri Lanka"]
    },
    "+95": {  # Myanmar
        "min_length": 9,
        "max_length": 10,
        "pattern": r"^9\d{8,9}$",
        "description": "9-10 digits, mobile starts with 9",
        "countries": ["Myanmar"]
    },
    "+98": {  # Iran
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^9\d{9}$",
        "description": "10 digits, mobile starts with 9",
        "countries": ["Iran"]
    },
    "+212": {  # Morocco
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[67]\d{8}$",
        "description": "9 digits, mobile starts with 6 or 7",
        "countries": ["Morocco"]
    },
    "+213": {  # Algeria
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[567]\d{8}$",
        "description": "9 digits, mobile starts with 5, 6, or 7",
        "countries": ["Algeria"]
    },
    "+216": {  # Tunisia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[2459]\d{7}$",
        "description": "8 digits",
        "countries": ["Tunisia"]
    },
    "+218": {  # Libya
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Libya"]
    },
    "+220": {  # Gambia
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[0-9]{7}$",
        "description": "7 digits",
        "countries": ["Gambia"]
    },
    "+221": {  # Senegal
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[0678]\d{7}$",
        "description": "9 digits, mobile starts with 70, 76, 77, or 78",
        "countries": ["Senegal"]
    },
    "+223": {  # Mali
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[67]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 7",
        "countries": ["Mali"]
    },
    "+224": {  # Guinea
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6\d{8}$",
        "description": "9 digits, mobile starts with 6",
        "countries": ["Guinea"]
    },
    "+225": {  # Ivory Coast
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[0-9]{10}$",
        "description": "10 digits",
        "countries": ["Ivory Coast"]
    },
    "+226": {  # Burkina Faso
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[567]\d{7}$",
        "description": "8 digits, mobile starts with 5, 6, or 7",
        "countries": ["Burkina Faso"]
    },
    "+227": {  # Niger
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[89]\d{7}$",
        "description": "8 digits, mobile starts with 8 or 9",
        "countries": ["Niger"]
    },
    "+228": {  # Togo
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^9\d{7}$",
        "description": "8 digits, mobile starts with 9",
        "countries": ["Togo"]
    },
    "+229": {  # Benin
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[69]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 9",
        "countries": ["Benin"]
    },
    "+230": {  # Mauritius
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^5\d{7}$",
        "description": "8 digits, mobile starts with 5",
        "countries": ["Mauritius"]
    },
    "+231": {  # Liberia
        "min_length": 7,
        "max_length": 8,
        "pattern": r"^[7789]\d{6,7}$",
        "description": "7-8 digits, mobile starts with 77, 78, 88, or 89",
        "countries": ["Liberia"]
    },
    "+232": {  # Sierra Leone
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[37]\d{7}$",
        "description": "8 digits, mobile starts with 3 or 7",
        "countries": ["Sierra Leone"]
    },
    "+233": {  # Ghana
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[235]\d{8}$",
        "description": "9 digits, mobile starts with 2, 3, or 5",
        "countries": ["Ghana"]
    },
    "+234": {  # Nigeria
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^[789]\d{9}$",
        "description": "10 digits, mobile starts with 7, 8, or 9",
        "countries": ["Nigeria"]
    },
    "+235": {  # Chad
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[69]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 9",
        "countries": ["Chad"]
    },
    "+236": {  # Central African Republic
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^7\d{7}$",
        "description": "8 digits, mobile starts with 7",
        "countries": ["Central African Republic"]
    },
    "+237": {  # Cameroon
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6[5678]\d{7}$",
        "description": "9 digits, mobile starts with 65, 66, 67, or 68",
        "countries": ["Cameroon"]
    },
    "+238": {  # Cape Verde
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[59]\d{6}$",
        "description": "7 digits, mobile starts with 5 or 9",
        "countries": ["Cape Verde"]
    },
    "+239": {  # Sao Tome and Principe
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^9\d{6}$",
        "description": "7 digits, mobile starts with 9",
        "countries": ["Sao Tome and Principe"]
    },
    "+240": {  # Equatorial Guinea
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[235]\d{8}$",
        "description": "9 digits, mobile starts with 2, 3, or 5",
        "countries": ["Equatorial Guinea"]
    },
    "+241": {  # Gabon
        "min_length": 7,
        "max_length": 8,
        "pattern": r"^[02467]\d{6,7}$",
        "description": "7-8 digits",
        "countries": ["Gabon"]
    },
    "+242": {  # Congo
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^0[456]\d{7}$",
        "description": "9 digits, mobile starts with 04, 05, or 06",
        "countries": ["Congo"]
    },
    "+243": {  # Democratic Republic of the Congo
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[89]\d{8}$",
        "description": "9 digits, mobile starts with 8 or 9",
        "countries": ["Democratic Republic of the Congo"]
    },
    "+244": {  # Angola
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Angola"]
    },
    "+245": {  # Guinea-Bissau
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[56]\d{6}$",
        "description": "7 digits, mobile starts with 5 or 6",
        "countries": ["Guinea-Bissau"]
    },
    "+246": {  # British Indian Ocean Territory
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[0-9]{7}$",
        "description": "7 digits",
        "countries": ["British Indian Ocean Territory"]
    },
    "+248": {  # Seychelles
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[2567]\d{6}$",
        "description": "7 digits, mobile starts with 2, 5, 6, or 7",
        "countries": ["Seychelles"]
    },
    "+249": {  # Sudan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[19]\d{8}$",
        "description": "9 digits, mobile starts with 1 or 9",
        "countries": ["Sudan"]
    },
    "+250": {  # Rwanda
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[238]\d{7}$",
        "description": "9 digits, mobile starts with 72, 73, or 78",
        "countries": ["Rwanda"]
    },
    "+251": {  # Ethiopia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Ethiopia"]
    },
    "+252": {  # Somalia
        "min_length": 8,
        "max_length": 9,
        "pattern": r"^[67]\d{7,8}$",
        "description": "8-9 digits, mobile starts with 6 or 7",
        "countries": ["Somalia"]
    },
    "+253": {  # Djibouti
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^77\d{6}$",
        "description": "8 digits, mobile starts with 77",
        "countries": ["Djibouti"]
    },
    "+254": {  # Kenya
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[71]\d{8}$",
        "description": "9 digits, mobile starts with 7 or 1",
        "countries": ["Kenya"]
    },
    "+255": {  # Tanzania
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[67]\d{8}$",
        "description": "9 digits, mobile starts with 6 or 7",
        "countries": ["Tanzania"]
    },
    "+256": {  # Uganda
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[37]\d{8}$",
        "description": "9 digits, mobile starts with 3 or 7",
        "countries": ["Uganda"]
    },
    "+257": {  # Burundi
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[67]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 7",
        "countries": ["Burundi"]
    },
    "+258": {  # Mozambique
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^8[234567]\d{7}$",
        "description": "9 digits, mobile starts with 82-87",
        "countries": ["Mozambique"]
    },
    "+260": {  # Zambia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[79]\d{8}$",
        "description": "9 digits, mobile starts with 7 or 9",
        "countries": ["Zambia"]
    },
    "+261": {  # Madagascar
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^3[234]\d{7}$",
        "description": "9 digits, mobile starts with 32, 33, or 34",
        "countries": ["Madagascar"]
    },
    "+262": {  # Reunion
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6\d{8}$",
        "description": "9 digits, mobile starts with 6",
        "countries": ["Reunion"]
    },
    "+263": {  # Zimbabwe
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[137]\d{7}$",
        "description": "9 digits, mobile starts with 71, 73, or 77",
        "countries": ["Zimbabwe"]
    },
    "+264": {  # Namibia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[68]\d{8}$",
        "description": "9 digits, mobile starts with 6 or 8",
        "countries": ["Namibia"]
    },
    "+265": {  # Malawi
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[89]\d{8}$",
        "description": "9 digits, mobile starts with 8 or 9",
        "countries": ["Malawi"]
    },
    "+266": {  # Lesotho
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[56]\d{7}$",
        "description": "8 digits, mobile starts with 5 or 6",
        "countries": ["Lesotho"]
    },
    "+267": {  # Botswana
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^7[1234567]\d{6}$",
        "description": "8 digits, mobile starts with 71-77",
        "countries": ["Botswana"]
    },
    "+268": {  # Eswatini
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^7[689]\d{6}$",
        "description": "8 digits, mobile starts with 76, 78, or 79",
        "countries": ["Eswatini"]
    },
    "+269": {  # Comoros
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[37]\d{6}$",
        "description": "7 digits, mobile starts with 3 or 7",
        "countries": ["Comoros"]
    },
    "+290": {  # Saint Helena
        "min_length": 4,
        "max_length": 5,
        "pattern": r"^[0-9]{4,5}$",
        "description": "4-5 digits",
        "countries": ["Saint Helena"]
    },
    "+291": {  # Eritrea
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[17]\d{6}$",
        "description": "7 digits, mobile starts with 1 or 7",
        "countries": ["Eritrea"]
    },
    "+297": {  # Aruba
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[567]\d{6}$",
        "description": "7 digits, mobile starts with 5, 6, or 7",
        "countries": ["Aruba"]
    },
    "+298": {  # Faroe Islands
        "min_length": 6,
        "max_length": 6,
        "pattern": r"^[0-9]{6}$",
        "description": "6 digits",
        "countries": ["Faroe Islands"]
    },
    "+299": {  # Greenland
        "min_length": 6,
        "max_length": 6,
        "pattern": r"^[245]\d{5}$",
        "description": "6 digits, mobile starts with 2, 4, or 5",
        "countries": ["Greenland"]
    },
    "+350": {  # Gibraltar
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[56]\d{7}$",
        "description": "8 digits, mobile starts with 5 or 6",
        "countries": ["Gibraltar"]
    },
    "+351": {  # Portugal
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9[1236]\d{7}$",
        "description": "9 digits, mobile starts with 91, 92, 93, or 96",
        "countries": ["Portugal"]
    },
    "+352": {  # Luxembourg
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6[0-9]{8}$",
        "description": "9 digits, mobile starts with 6",
        "countries": ["Luxembourg"]
    },
    "+353": {  # Ireland
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^8[356789]\d{7}$",
        "description": "9 digits, mobile starts with 83, 85, 86, 87, 88, or 89",
        "countries": ["Ireland"]
    },
    "+354": {  # Iceland
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[678]\d{6}$",
        "description": "7 digits, mobile starts with 6, 7, or 8",
        "countries": ["Iceland"]
    },
    "+355": {  # Albania
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6[789]\d{7}$",
        "description": "9 digits, mobile starts with 67, 68, or 69",
        "countries": ["Albania"]
    },
    "+356": {  # Malta
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[79]\d{7}$",
        "description": "8 digits, mobile starts with 7 or 9",
        "countries": ["Malta"]
    },
    "+357": {  # Cyprus
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^9[456789]\d{6}$",
        "description": "8 digits, mobile starts with 94-99",
        "countries": ["Cyprus"]
    },
    "+358": {  # Finland
        "min_length": 9,
        "max_length": 10,
        "pattern": r"^[45]\d{8,9}$",
        "description": "9-10 digits, mobile starts with 4 or 5",
        "countries": ["Finland"]
    },
    "+359": {  # Bulgaria
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^8[789]\d{7}$",
        "description": "9 digits, mobile starts with 87, 88, or 89",
        "countries": ["Bulgaria"]
    },
    "+370": {  # Lithuania
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^6\d{7}$",
        "description": "8 digits, mobile starts with 6",
        "countries": ["Lithuania"]
    },
    "+371": {  # Latvia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^2\d{7}$",
        "description": "8 digits, mobile starts with 2",
        "countries": ["Latvia"]
    },
    "+372": {  # Estonia
        "min_length": 7,
        "max_length": 8,
        "pattern": r"^5\d{6,7}$",
        "description": "7-8 digits, mobile starts with 5",
        "countries": ["Estonia"]
    },
    "+373": {  # Moldova
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[67]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 7",
        "countries": ["Moldova"]
    },
    "+374": {  # Armenia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[4579]\d{7}$",
        "description": "8 digits, mobile starts with 4, 5, 7, or 9",
        "countries": ["Armenia"]
    },
    "+375": {  # Belarus
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[234]\d{8}$",
        "description": "9 digits, mobile starts with 2, 3, or 4",
        "countries": ["Belarus"]
    },
    "+376": {  # Andorra
        "min_length": 6,
        "max_length": 6,
        "pattern": r"^[346]\d{5}$",
        "description": "6 digits, mobile starts with 3, 4, or 6",
        "countries": ["Andorra"]
    },
    "+377": {  # Monaco
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[46]\d{7}$",
        "description": "8 digits, mobile starts with 4 or 6",
        "countries": ["Monaco"]
    },
    "+378": {  # San Marino
        "min_length": 8,
        "max_length": 10,
        "pattern": r"^6[0-9]{7,9}$",
        "description": "8-10 digits, mobile starts with 6",
        "countries": ["San Marino"]
    },
    "+380": {  # Ukraine
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[3456789]\d{8}$",
        "description": "9 digits",
        "countries": ["Ukraine"]
    },
    "+381": {  # Serbia
        "min_length": 8,
        "max_length": 9,
        "pattern": r"^6[0-9]{7,8}$",
        "description": "8-9 digits, mobile starts with 6",
        "countries": ["Serbia"]
    },
    "+382": {  # Montenegro
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^6[789]\d{6}$",
        "description": "8 digits, mobile starts with 67, 68, or 69",
        "countries": ["Montenegro"]
    },
    "+383": {  # Kosovo
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^4[3456789]\d{6}$",
        "description": "8 digits, mobile starts with 43-49",
        "countries": ["Kosovo"]
    },
    "+385": {  # Croatia
        "min_length": 8,
        "max_length": 9,
        "pattern": r"^9[12589]\d{6,7}$",
        "description": "8-9 digits, mobile starts with 91, 92, 95, 98, or 99",
        "countries": ["Croatia"]
    },
    "+386": {  # Slovenia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[34567]\d{7}$",
        "description": "8 digits, mobile starts with 3, 4, 5, 6, or 7",
        "countries": ["Slovenia"]
    },
    "+387": {  # Bosnia and Herzegovina
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^6[0123456]\d{6}$",
        "description": "8 digits, mobile starts with 60-66",
        "countries": ["Bosnia and Herzegovina"]
    },
    "+389": {  # North Macedonia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^7[01234578]\d{6}$",
        "description": "8 digits, mobile starts with 70-75, 77, or 78",
        "countries": ["North Macedonia"]
    },
    "+420": {  # Czech Republic
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[67]\d{8}$",
        "description": "9 digits, mobile starts with 6 or 7",
        "countries": ["Czech Republic"]
    },
    "+421": {  # Slovakia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9[01]\d{7}$",
        "description": "9 digits, mobile starts with 90 or 91",
        "countries": ["Slovakia"]
    },
    "+423": {  # Liechtenstein
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[67]\d{6}$",
        "description": "7 digits, mobile starts with 6 or 7",
        "countries": ["Liechtenstein"]
    },
    "+500": {  # Falkland Islands
        "min_length": 5,
        "max_length": 5,
        "pattern": r"^[56]\d{4}$",
        "description": "5 digits, mobile starts with 5 or 6",
        "countries": ["Falkland Islands"]
    },
    "+501": {  # Belize
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^6[0-9]{6}$",
        "description": "7 digits, mobile starts with 6",
        "countries": ["Belize"]
    },
    "+502": {  # Guatemala
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[3456]\d{7}$",
        "description": "8 digits, mobile starts with 3, 4, 5, or 6",
        "countries": ["Guatemala"]
    },
    "+503": {  # El Salvador
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[67]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 7",
        "countries": ["El Salvador"]
    },
    "+504": {  # Honduras
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[389]\d{7}$",
        "description": "8 digits, mobile starts with 3, 8, or 9",
        "countries": ["Honduras"]
    },
    "+505": {  # Nicaragua
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[578]\d{7}$",
        "description": "8 digits, mobile starts with 5, 7, or 8",
        "countries": ["Nicaragua"]
    },
    "+506": {  # Costa Rica
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[56789]\d{7}$",
        "description": "8 digits",
        "countries": ["Costa Rica"]
    },
    "+507": {  # Panama
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^6\d{7}$",
        "description": "8 digits, mobile starts with 6",
        "countries": ["Panama"]
    },
    "+508": {  # Saint Pierre and Miquelon
        "min_length": 6,
        "max_length": 6,
        "pattern": r"^[45]\d{5}$",
        "description": "6 digits, mobile starts with 4 or 5",
        "countries": ["Saint Pierre and Miquelon"]
    },
    "+509": {  # Haiti
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[34]\d{7}$",
        "description": "8 digits, mobile starts with 3 or 4",
        "countries": ["Haiti"]
    },
    "+590": {  # Guadeloupe
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6\d{8}$",
        "description": "9 digits, mobile starts with 6",
        "countries": ["Guadeloupe"]
    },
    "+591": {  # Bolivia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[67]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 7",
        "countries": ["Bolivia"]
    },
    "+592": {  # Guyana
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^6\d{6}$",
        "description": "7 digits, mobile starts with 6",
        "countries": ["Guyana"]
    },
    "+593": {  # Ecuador
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Ecuador"]
    },
    "+594": {  # French Guiana
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6\d{8}$",
        "description": "9 digits, mobile starts with 6",
        "countries": ["French Guiana"]
    },
    "+595": {  # Paraguay
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Paraguay"]
    },
    "+596": {  # Martinique
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^6\d{8}$",
        "description": "9 digits, mobile starts with 6",
        "countries": ["Martinique"]
    },
    "+597": {  # Suriname
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[78]\d{6}$",
        "description": "7 digits, mobile starts with 7 or 8",
        "countries": ["Suriname"]
    },
    "+598": {  # Uruguay
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^9\d{7}$",
        "description": "8 digits, mobile starts with 9",
        "countries": ["Uruguay"]
    },
    "+599": {  # Netherlands Antilles
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[569]\d{6}$",
        "description": "7 digits, mobile starts with 5, 6, or 9",
        "countries": ["Netherlands Antilles"]
    },
    "+670": {  # East Timor
        "min_length": 7,
        "max_length": 8,
        "pattern": r"^7[234678]\d{5,6}$",
        "description": "7-8 digits, mobile starts with 72-74, 76-78",
        "countries": ["East Timor"]
    },
    "+672": {  # Norfolk Island
        "min_length": 5,
        "max_length": 6,
        "pattern": r"^[35]\d{4,5}$",
        "description": "5-6 digits, mobile starts with 3 or 5",
        "countries": ["Norfolk Island"]
    },
    "+673": {  # Brunei
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[78]\d{6}$",
        "description": "7 digits, mobile starts with 7 or 8",
        "countries": ["Brunei"]
    },
    "+674": {  # Nauru
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^55\d{5}$",
        "description": "7 digits, mobile starts with 55",
        "countries": ["Nauru"]
    },
    "+675": {  # Papua New Guinea
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^7\d{7}$",
        "description": "8 digits, mobile starts with 7",
        "countries": ["Papua New Guinea"]
    },
    "+676": {  # Tonga
        "min_length": 5,
        "max_length": 7,
        "pattern": r"^[78]\d{4,6}$",
        "description": "5-7 digits, mobile starts with 7 or 8",
        "countries": ["Tonga"]
    },
    "+677": {  # Solomon Islands
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[78]\d{6}$",
        "description": "7 digits, mobile starts with 7 or 8",
        "countries": ["Solomon Islands"]
    },
    "+678": {  # Vanuatu
        "min_length": 5,
        "max_length": 7,
        "pattern": r"^[57]\d{4,6}$",
        "description": "5-7 digits, mobile starts with 5 or 7",
        "countries": ["Vanuatu"]
    },
    "+679": {  # Fiji
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[7-9]\d{6}$",
        "description": "7 digits, mobile starts with 7, 8, or 9",
        "countries": ["Fiji"]
    },
    "+680": {  # Palau
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[67]\d{6}$",
        "description": "7 digits, mobile starts with 6 or 7",
        "countries": ["Palau"]
    },
    "+681": {  # Wallis and Futuna
        "min_length": 6,
        "max_length": 6,
        "pattern": r"^[57]\d{5}$",
        "description": "6 digits, mobile starts with 5 or 7",
        "countries": ["Wallis and Futuna"]
    },
    "+682": {  # Cook Islands
        "min_length": 5,
        "max_length": 5,
        "pattern": r"^[57]\d{4}$",
        "description": "5 digits, mobile starts with 5 or 7",
        "countries": ["Cook Islands"]
    },
    "+683": {  # Niue
        "min_length": 4,
        "max_length": 4,
        "pattern": r"^[0-9]{4}$",
        "description": "4 digits",
        "countries": ["Niue"]
    },
    "+684": {  # American Samoa
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[27]\d{6}$",
        "description": "7 digits, mobile starts with 2 or 7",
        "countries": ["American Samoa"]
    },
    "+685": {  # Samoa
        "min_length": 5,
        "max_length": 7,
        "pattern": r"^[78]\d{4,6}$",
        "description": "5-7 digits, mobile starts with 7 or 8",
        "countries": ["Samoa"]
    },
    "+686": {  # Kiribati
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[67]\d{7}$",
        "description": "8 digits, mobile starts with 6 or 7",
        "countries": ["Kiribati"]
    },
    "+687": {  # New Caledonia
        "min_length": 6,
        "max_length": 6,
        "pattern": r"^[789]\d{5}$",
        "description": "6 digits, mobile starts with 7, 8, or 9",
        "countries": ["New Caledonia"]
    },
    "+688": {  # Tuvalu
        "min_length": 5,
        "max_length": 5,
        "pattern": r"^9\d{4}$",
        "description": "5 digits, mobile starts with 9",
        "countries": ["Tuvalu"]
    },
    "+689": {  # French Polynesia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^8[79]\d{6}$",
        "description": "8 digits, mobile starts with 87 or 89",
        "countries": ["French Polynesia"]
    },
    "+690": {  # Tokelau
        "min_length": 4,
        "max_length": 5,
        "pattern": r"^[0-9]{4,5}$",
        "description": "4-5 digits",
        "countries": ["Tokelau"]
    },
    "+691": {  # Micronesia
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[39]\d{6}$",
        "description": "7 digits, mobile starts with 3 or 9",
        "countries": ["Micronesia"]
    },
    "+692": {  # Marshall Islands
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[2456]\d{6}$",
        "description": "7 digits, mobile starts with 2, 4, 5, or 6",
        "countries": ["Marshall Islands"]
    },
    "+850": {  # North Korea
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^19[123]\d{7}$",
        "description": "10 digits, mobile starts with 191, 192, or 193",
        "countries": ["North Korea"]
    },
    "+852": {  # Hong Kong
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[569]\d{7}$",
        "description": "8 digits, mobile starts with 5, 6, or 9",
        "countries": ["Hong Kong"]
    },
    "+853": {  # Macau
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^6[0-9]{7}$",
        "description": "8 digits, mobile starts with 6",
        "countries": ["Macau"]
    },
    "+855": {  # Cambodia
        "min_length": 8,
        "max_length": 9,
        "pattern": r"^[1789]\d{7,8}$",
        "description": "8-9 digits, mobile starts with 1, 7, 8, or 9",
        "countries": ["Cambodia"]
    },
    "+856": {  # Laos
        "min_length": 9,
        "max_length": 10,
        "pattern": r"^20[0-9]{7,8}$",
        "description": "9-10 digits, mobile starts with 20",
        "countries": ["Laos"]
    },
    "+880": {  # Bangladesh
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^1[3-9]\d{8}$",
        "description": "10 digits, mobile starts with 13-19",
        "countries": ["Bangladesh"]
    },
    "+886": {  # Taiwan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Taiwan"]
    },
    "+960": {  # Maldives
        "min_length": 7,
        "max_length": 7,
        "pattern": r"^[79]\d{6}$",
        "description": "7 digits, mobile starts with 7 or 9",
        "countries": ["Maldives"]
    },
    "+961": {  # Lebanon
        "min_length": 7,
        "max_length": 8,
        "pattern": r"^[37]\d{6,7}$",
        "description": "7-8 digits, mobile starts with 3 or 7",
        "countries": ["Lebanon"]
    },
    "+962": {  # Jordan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[789]\d{7}$",
        "description": "9 digits, mobile starts with 77, 78, or 79",
        "countries": ["Jordan"]
    },
    "+963": {  # Syria
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9\d{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Syria"]
    },
    "+964": {  # Iraq
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^7[3-9]\d{8}$",
        "description": "10 digits, mobile starts with 73-79",
        "countries": ["Iraq"]
    },
    "+965": {  # Kuwait
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[569]\d{7}$",
        "description": "8 digits, mobile starts with 5, 6, or 9",
        "countries": ["Kuwait"]
    },
    "+966": {  # Saudi Arabia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^5[0-9]{8}$",
        "description": "9 digits, mobile starts with 5",
        "countries": ["Saudi Arabia"]
    },
    "+967": {  # Yemen
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^7[01234567]\d{7}$",
        "description": "9 digits, mobile starts with 70-77",
        "countries": ["Yemen"]
    },
    "+968": {  # Oman
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[79]\d{7}$",
        "description": "8 digits, mobile starts with 7 or 9",
        "countries": ["Oman"]
    },
    "+970": {  # Palestine
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^5[69]\d{7}$",
        "description": "9 digits, mobile starts with 56 or 59",
        "countries": ["Palestine"]
    },
    "+971": {  # United Arab Emirates
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^5[024568]\d{7}$",
        "description": "9 digits, mobile starts with 50, 52, 54, 55, 56, or 58",
        "countries": ["United Arab Emirates"]
    },
    "+972": {  # Israel
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^5[0-9]{8}$",
        "description": "9 digits, mobile starts with 5",
        "countries": ["Israel"]
    },
    "+973": {  # Bahrain
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[3679]\d{7}$",
        "description": "8 digits, mobile starts with 3, 6, 7, or 9",
        "countries": ["Bahrain"]
    },
    "+974": {  # Qatar
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[3567]\d{7}$",
        "description": "8 digits, mobile starts with 3, 5, 6, or 7",
        "countries": ["Qatar"]
    },
    "+975": {  # Bhutan
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[17]\d{7}$",
        "description": "8 digits, mobile starts with 1 or 7",
        "countries": ["Bhutan"]
    },
    "+976": {  # Mongolia
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^[89]\d{7}$",
        "description": "8 digits, mobile starts with 8 or 9",
        "countries": ["Mongolia"]
    },
    "+977": {  # Nepal
        "min_length": 10,
        "max_length": 10,
        "pattern": r"^9[78]\d{8}$",
        "description": "10 digits, mobile starts with 97 or 98",
        "countries": ["Nepal"]
    },
    "+992": {  # Tajikistan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9[01234789]\d{7}$",
        "description": "9 digits, mobile starts with 90-94, 97-99",
        "countries": ["Tajikistan"]
    },
    "+993": {  # Turkmenistan
        "min_length": 8,
        "max_length": 8,
        "pattern": r"^6[1-5]\d{6}$",
        "description": "8 digits, mobile starts with 61-65",
        "countries": ["Turkmenistan"]
    },
    "+994": {  # Azerbaijan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[4567]\d{8}$",
        "description": "9 digits, mobile starts with 4, 5, 6, or 7",
        "countries": ["Azerbaijan"]
    },
    "+995": {  # Georgia
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^5[0-9]{8}$",
        "description": "9 digits, mobile starts with 5",
        "countries": ["Georgia"]
    },
    "+996": {  # Kyrgyzstan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^[57]\d{8}$",
        "description": "9 digits, mobile starts with 5 or 7",
        "countries": ["Kyrgyzstan"]
    },
    "+998": {  # Uzbekistan
        "min_length": 9,
        "max_length": 9,
        "pattern": r"^9[0-9]{8}$",
        "description": "9 digits, mobile starts with 9",
        "countries": ["Uzbekistan"]
    }
}


def validate_phone_number(phone_number: str, country_code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a phone number based on the country code.
    
    Args:
        phone_number: The phone number to validate (digits only)
        country_code: The country code including the + prefix
    
    Returns:
        A tuple of (is_valid, error_message)
        - is_valid: True if the phone number is valid, False otherwise
        - error_message: Error message if invalid, None if valid
    """
    # Clean the phone number (remove any non-digit characters)
    cleaned_number = re.sub(r'\D', '', phone_number)
    
    # Check if we have validation rules for this country code
    if country_code not in PHONE_VALIDATION_RULES:
        # Default validation for unknown country codes
        if len(cleaned_number) < 7 or len(cleaned_number) > 15:
            return False, f"Phone number must be between 7 and 15 digits for country code {country_code}"
        return True, None
    
    # Get the validation rules for this country code
    rules = PHONE_VALIDATION_RULES[country_code]
    
    # Check length
    if len(cleaned_number) < rules["min_length"]:
        return False, f"Phone number must be at least {rules['min_length']} digits for {', '.join(rules['countries'])}"
    
    if len(cleaned_number) > rules["max_length"]:
        return False, f"Phone number must be at most {rules['max_length']} digits for {', '.join(rules['countries'])}"
    
    # Check pattern
    if not re.match(rules["pattern"], cleaned_number):
        return False, f"Invalid phone number format for {', '.join(rules['countries'])}. {rules['description']}"
    
    return True, None


def get_country_info(country_code: str) -> Optional[Dict[str, any]]:
    """
    Get information about a country code.
    
    Args:
        country_code: The country code including the + prefix
    
    Returns:
        Dictionary with country information or None if not found
    """
    if country_code in PHONE_VALIDATION_RULES:
        return PHONE_VALIDATION_RULES[country_code]
    return None
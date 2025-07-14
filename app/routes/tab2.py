from flask import Blueprint, render_template, request, jsonify
from collections import defaultdict
from db_connection import DatabaseConnection
import sqlite3

tab2_bp = Blueprint("tab2_bp", __name__, url_prefix="/tab2")

# Hardcoded mappings from seed data
CATEGORY_MAP = {
    # Tent Tops
    4052: 'Tent Tops',  # SIDEWALL HP 10 x 8 WHITE
    4054: 'Tent Tops',  # Canopy 20x20 HP TOP SKYLIGHT
    4203: 'Tent Tops',  # TOP NAVI LITE 30x15 HIP G1
    4204: 'Tent Tops',  # TOP NAVI LITE 30x15 MID G1
    4213: 'Tent Tops',  # SIDEWALL NAVI LITE 8x 15 WINDOW KEDAR
    4214: 'Tent Tops',  # SIDEWALL NAVI LITE 8 x 15 WHITE KEDAR
    4292: 'Tent Tops',  # Canopy 20x30 HP TOP WHITE Single Peak
    4807: 'Tent Tops',  # SIDEWALL HP 15 x 9 WINDOW (G1)
    4808: 'Tent Tops',  # SIDEWALL HP 15 x 9 WHITE (G1)
    60526: 'Tent Tops',  # SIDEWALL KEDARNAVI 15x8 (G1) WINDOW
    60528: 'Tent Tops',  # SIDEWALL KEDAR NAVI 15x8 (G1) WHITE
    62706: 'Tent Tops',  # TOP HP 10 X 10 (G1)
    62707: 'Tent Tops',  # TOP HP 10 X 20 (G2)
    62708: 'Tent Tops',  # TOP HP 15X15 (G1)
    62709: 'Tent Tops',  # TOP HP 20 X 20 (G2)
    62711: 'Tent Tops',  # TOP HP 30 X 30 (G1)
    62714: 'Tent Tops',  # TOP HP HEX 35 X 40 WHITE
    62715: 'Tent Tops',  # SIDEWALL HP 15 x 8 (G1) WINDOW
    62719: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G1) w/DOOR/WIND
    62723: 'Tent Tops',  # SIDEWALL HP 10 x 8 (G1) WINDOW
    62727: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G1) WINDOW
    62731: 'Tent Tops',  # SIDEWALL HP 30 x 8 (G1) WINDOW
    62735: 'Tent Tops',  # SIDEWALL HP 20 x 9 (G1) WINDOW
    62737: 'Tent Tops',  # SIDEWALL HP 20 x 9 (G3) WINDOW
    62745: 'Tent Tops',  # SIDEWALL HP 15 x 8 (G1) w/DOOR
    62749: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G1) w/DOOR pole
    62750: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G2) w/DOOR pole
    62753: 'Tent Tops',  # SIDEWALL HP 10 x 8 (G1) WHITE
    62755: 'Tent Tops',  # SIDEWALL HP 10 x 8 (G3) WHITE
    62757: 'Tent Tops',  # SIDEWALL HP 15 x 8 (G1) WHITE
    62761: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G1) WHITE
    62762: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G2) WHITE
    62763: 'Tent Tops',  # SIDEWALL HP 20 x 8 (G3) WHITE
    62769: 'Tent Tops',  # SIDEWALL HP 20 x 9 (G1) WHITE
    62770: 'Tent Tops',  # SIDEWALL HP 20 x 9 (G2) WHITE
    62773: 'Tent Tops',  # SIDEWALL HP 20 x 7 (G1) WHITE
    62781: 'Tent Tops',  # SIDEWALL HP 30 x 8 (G1) WHITE pole
    62782: 'Tent Tops',  # SIDEWALL HP 30 x 8 (G2) WHITE pole
    62805: 'Tent Tops',  # TOP NAVI 30x15 MID (G1)
    62806: 'Tent Tops',  # MID 30 x 15 (G1) R AND W POLE CMATE
    62807: 'Tent Tops',  # END 30 x 15 LACE (G1) R AND W POLE
    62808: 'Tent Tops',  # TOP NAVI 30x15 HIP
    62809: 'Tent Tops',  # MID 60 x 20 ANCHOR POLE NC (G1)
    62810: 'Tent Tops',  # MID 60 x 30 (G1) ANCHOR POLE NC
    62853: 'Tent Tops',  # SIDEWALLMESH 7 H X 20 (G1) WH
    62857: 'Tent Tops',  # SIDEWALL STD 7 X 20 (G1) WINDOW
    62858: 'Tent Tops',  # SIDEWALL STD 7 X 20 (G2) WINDOW
    62859: 'Tent Tops',  # SIDEWALL STD 7 X 20 (G3) WINDOW
    62861: 'Tent Tops',  # SIDEWALL STD 7 X 30 (G1) WINDOW
    62862: 'Tent Tops',  # SIDEWALL STD 7 X 30 (G2) WINDOW
    62864: 'Tent Tops',  # SIDEWALL STD 7 X 40 (G1) WINDOW
    62865: 'Tent Tops',  # SIDEWALL STD 7 X 40 (G2) WINDOW
    62867: 'Tent Tops',  # SIDEWALL STD 8 X 20 (G1) WINDOW
    62868: 'Tent Tops',  # SIDEWALL STD 8 X 20 (G2) WINDOW
    62871: 'Tent Tops',  # SIDEWALL NAVI 8 X 30 (G1) WINDOW
    62872: 'Tent Tops',  # SIDEWALL NAVI 8 X 30 (G2) WINDOW
    62875: 'Tent Tops',  # SIDEWALL STD 8 X 40 (G1) WINDOW
    62876: 'Tent Tops',  # SIDEWALL STD 8 X 40 (G2) WINDOW
    62883: 'Tent Tops',  # SIDEWALLEXTENDER 3 X 20 (G2)
    62887: 'Tent Tops',  # SIDEWALLEXTENDER 3 X 30 (G2)
    62891: 'Tent Tops',  # SIDEWALLEXTENDER 3 X 40 (G2)
    62894: 'Tent Tops',  # SIDEWALL STD 7 X 20 (G1) WHITE
    62895: 'Tent Tops',  # SIDEWALL STD 7 X 20 (G2) WHITE
    62896: 'Tent Tops',  # SIDEWALL STD 7 X 20 (G3) WHITE
    62797: 'Tent Tops',  # MID 40 x 20 (G1) NCP
    62798: 'Tent Tops',  # END 40 x 20 LACE (G1) NCP
    62900: 'Tent Tops',  # SIDEWALL STD 8 X 20 (G1) WHITE
    62901: 'Tent Tops',  # SIDEWALL STD 8 X 20 (G2) WHITE
    62902: 'Tent Tops',  # SIDEWALL STD 8 X 20 (G3) WHITE
    62904: 'Tent Tops',  # SIDEWALL NAVI 8 X 30 (G1) WHITE
    62905: 'Tent Tops',  # SIDEWALL NAVI 8 X 30 (G2) WHITE
    62906: 'Tent Tops',  # SIDEWALL NAVI 8 X 30 (G3) WHITE
    65035: 'Tent Tops',  # END 40 x 20 GRMT (G1) ANCHOR POLE NC
    65036: 'Tent Tops',  # END 60 x 20 LACE (G1) ANCHOR POLE NC
    65037: 'Tent Tops',  # END 60 x 20 GRMT (G1) ANCHOR POLE NC
    65039: 'Tent Tops',  # END 30 x 15 GRMT (G1) R AND W POLE
    65367: 'Tent Tops',  # TOP HP 20 X 20 (G1)
    65119: 'Tent Tops', #g1
    65446: 'Tent Tops',  # TOP HP HEX 35 X 40 SKYLIGHT
    65449: 'Tent Tops',  # TOP NAVI 15 GABLE ENDCAP LACE
    65450: 'Tent Tops',  # TOP NAVI 15 GABLE ENDCAP GRMT
    65467: 'Tent Tops',  # TOP NAVI 20 GABLE ENDCAP GRMT
    65468: 'Tent Tops',  # TOP NAVI 20 GABLE ENDCAP LACE
    65469: 'Tent Tops',  # TOP NAVI 40x15 MID (G1)
    66324: 'Tent Tops',  # TOP NAVI LITE 30x15 MID G2
    66325: 'Tent Tops',  # TOP NAVI 30x15 MID (G2)
    66326: 'Tent Tops',  # TOPS NAVI 30x15 MID
    67657: 'Tent Tops',  # TOP HP 20 X 30 (G1) WHITE DBL PEAK
    65129: 'Tent Tops',  # CANOPY 10X10 POPUP  WHITE WEIGHTED
    66363: 'Tent Tops',  # CANOPY AP 16X16 WHITE (R)(G1)
    72252: 'Tent Tops',  # SIDEWALL KEDAR -G 8' x 5' PANEL
    72253: 'Tent Tops',  # SIDEWALL KEDAR -R 8' x 5' PANEL
    72392: 'Tent Tops',  # TOP NAVI LITE 30x15 HIP G2
    72401: 'Tent Tops',  # "CRATE, HP 10 x 10 ASSEMBLY"
    72402: 'Tent Tops',  # "CRATE, HP 15 x 15 ASSEMBLY"
    72403: 'Tent Tops',  # "CRATE, HP 10 x 20 ASSEMBLY"
    72404: 'Tent Tops',  # "CRATE, HP 20 x 20 ASSEMBLY"
    72405: 'Tent Tops',  # "CRATE, HP 30 x 30 ASSEMBLY"
    72406: 'Tent Tops',  # "CRATE, HP HEX 35 x 40 ASSEMBLY"
    72407: 'Tent Tops',  # "CRATE, HP 20 x 30 ASSEMBLY"
    72408: 'Tent Tops',  # "CRATE, NAVI HIP ASSEMBLY"
    72409: 'Tent Tops',  # "CRATE, NAVI MID ASSEMBLY"
    72410: 'Tent Tops',  # "CRATE, NAVI LITE HIP ASSEMBLY"
    72411: 'Tent Tops',  # "CRATE, NAVI LITE MID ASSEMBLY"
    72412: 'Tent Tops',  # "CRATE, NAVI INSTALLATION"
    62668: 'Tent Tops',  # CANOPY AP 20X20 WHITE (Rope)(G1)
    62669: 'Tent Tops',  # CANOPY AP 20X20 WHITE (Rope)(G2)
    62681: 'Tent Tops',  # CANOPY AP 20X30 WHITE (Rope)(G2)
    62682: 'Tent Tops',  # CANOPY AP 20X30 WHITE (Rope)(G1)
    62683: 'Tent Tops',  # CANOPY AP 20X40 WHITE (Rope)(G1)
    62684: 'Tent Tops',  # CANOPY AP 20X40 WHITE (Rope)(G2)
    62686: 'Tent Tops',  # CANOPY AP 16X16 WHITE (R)(G2)
    62803: 'Tent Tops',  # CANOPY POLE 30 x 30 WHITE
    63851: 'Tent Tops',  # TOP 6 GABLE END CAP (FOR MARQUEE
    63852: 'Tent Tops',  # TOP 6X10 WHITE GABLE MID FOR FR
    # AV
    60533: 'AV Equipment',  # "BULLHORN MV10S, 16WATT (SMALL)"
    60537: 'AV Equipment',  # "BULLHORN MV16S, 20WATT (LARGE)"
    60731: 'AV Equipment',  # "BUBBLE MACHINE, 3 DOUBLE WANDS, 11"
    60735: 'AV Equipment',  # "FOG MACHINE, HAZE, MINI"
    61543: 'AV Equipment',  # "SOUND SYSTEM, BIG FOOT v1"
    61545: 'AV Equipment',  # "SOUND SYSTEM, BIGFOOT 1.9GhZ(AA)"
    61548: 'AV Equipment',  # "SOUND SYSTEM, MiniVOX 1.9GhZ(AA)"
    61566: 'AV Equipment',  # "MIC, WIRELESS, HANDHELD (AA BIG FOOT V1)"
    61570: 'AV Equipment',  # "MIC, WIRELESS, HANDHELD 1.9GhZ(AA)"
    61571: 'AV Equipment',  # "MIC WIRED, HANDHELD (MINI-VOX)"
    61572: 'AV Equipment',  # "MIC, WIRELESS, HANDHELD  1.9GhZ(AA)"
    61573: 'AV Equipment',  # "MIC, WIRELESS, LAPEL 1.9GhZ(AA)"
    63343: 'AV Equipment',  # FOG MACHINE (HAZE)
    63359: 'AV Equipment',  # "MIC, WIRELESS, HANDHELD (SHURE)"
    63430: 'AV Equipment',  # "PROJECTOR, LCD, 4000 LUMENS 1080P"

    # Tables and Chairs
   63131: 'Tables and Chairs',  # "TOP, TABLE ROUND, 30 INCH PLYWOOD"
    63133: 'Tables and Chairs',  # LEG BASE 24 - 4 PRONG X
    65171: 'Tables and Chairs',  # LEG BASE 30 - 4 PRONG X FOR 36R
    65722: 'Tables and Chairs',  # "TOP, TABLE ROUND, 36 INCH PLYWOOD"
    61771: 'Tables and Chairs',  # CHAIRPAD CHIAVARI 2 BLACK (VEL
    61772: 'Tables and Chairs',  # CHAIRPAD CHIAVARI WHITE VINYL (

    # Round Linen
    61824: 'Round Linen',  # 90 ROUND  SNOW WHITE LINEN (SEAML
    61825: 'Round Linen',  # 90 ROUND  WHITE LINEN
    61826: 'Round Linen',  # 90 ROUND BLACK LINEN
    61882: 'Round Linen', #90r bermuda
    61883: 'Round Linen', #90r apple
    61827: 'Round Linen',  # 90 ROUND GREY LINEN
    61828: 'Round Linen',  # 90 ROUND IVORY LINEN
    61830: 'Round Linen',  # 90 ROUND KHAKI LINEN
    61831: 'Round Linen',  # 90 ROUND CHOCOLATE LINEN
    61832: 'Round Linen',  # 90 ROUND LEMON YELLOW LINEN
    61833: 'Round Linen',  # 90 ROUND MAIZE LINEN
    61834: 'Round Linen',  # 90 ROUND BYZANTINE FALL GOLD LINE
    61835: 'Round Linen',  # 90 ROUND POPPY LINEN
    61836: 'Round Linen',  # 90 ROUND PEACH LINEN
    61837: 'Round Linen',  # 90 ROUND ORANGE LINEN
    61838: 'Round Linen',  # 90 ROUND BURNT ORANGE LINEN
    61839: 'Round Linen',  # 90 ROUND SHRIMP LINEN
    61840: 'Round Linen',  # 90 ROUND RED LINEN
    61842: 'Round Linen',  # 90 ROUND CARDINAL RED LINEN
    61843: 'Round Linen',  # 90 ROUND HOT PINK LINEN
    61846: 'Round Linen',  # 90 ROUND PASTEL PINK LINEN
    61847: 'Round Linen',  # 90 ROUND PINK LINEN
    61848: 'Round Linen',  # 90 ROUND MAGENTA LINEN
    61850: 'Round Linen',  # 90 ROUND BURGUNDY LINEN
    61852: 'Round Linen',  # 90 ROUND GRAPE LINEN
    61854: 'Round Linen',  # 90 ROUND EGGPLANT LINEN
    61856: 'Round Linen',  # 90 ROUND AMETHYST LINEN
    61858: 'Round Linen',  # 90 ROUND ROYAL BLUE LINEN
    61859: 'Round Linen',  # 90 ROUND LIGHT BLUE LINEN
    61862: 'Round Linen',  # 90 ROUND TURQUOISE LINEN
    61863: 'Round Linen',  # 90 ROUND OCEAN BLUE LINEN
    61864: 'Round Linen',  # 90 ROUND PACIFICA LINEN
    61865: 'Round Linen',  # 90 ROUND PERIWINKLE LINEN
    61866: 'Round Linen',  # 90 ROUND NAVY BLUE LINEN
    61867: 'Round Linen',  # 90 ROUND CELADON LINEN
    61868: 'Round Linen',  # 90 ROUND HUNTER GREEN LINEN
    61869: 'Round Linen',  # 90 ROUND KELLY GREEN LINEN
    61870: 'Round Linen',  # 90 ROUND LIME GREEN LINEN
    61871: 'Round Linen',  # 90 ROUND ZEBRA PRINT LINEN
    61872: 'Round Linen',  # 90 ROUND PLATINUM IRIDESCENT CRUS
    61873: 'Round Linen',  # 90 ROUND CHAMPAGNE IRIDESCENT CRU
    61874: 'Round Linen',  # 90 ROUND  WHITE SAND IRIDESCENT C
    61875: 'Round Linen',  # 90 ROUND ROSE IRIDESCENT CRUSH LI
    61876: 'Round Linen',  # 90 ROUND VIOLET GREEN IRIDESCENT
    61879: 'Round Linen',  # 90 ROUND MIMOSA NOVA SOLID LINE
    61880: 'Round Linen',  # 90 ROUND FUCHSIA NOVA SOLID LIN
    61881: 'Round Linen',  # 90 ROUND TIFFANY BLUE NOVA SOLID
    61885: 'Round Linen',  # 108 ROUND WHITE LINEN
    61886: 'Round Linen',  # 108 ROUND BLACK LINEN
    61887: 'Round Linen',  # 108 ROUND GREY LINEN
    61888: 'Round Linen',  # 108 ROUND PEWTER LINEN
    61889: 'Round Linen',  # 108 ROUND IVORY LINEN
    61890: 'Round Linen',  # 108 ROUND BEIGE LINEN
    72595: 'Round Linen',  # 108 byz
    61891: 'Round Linen',  # 108 ROUND CHOCOLATE LINEN
    61893: 'Round Linen',  # 108 ROUND MAIZE LINEN
    61895: 'Round Linen',  # 108 ROUND POPPY LINEN
    61896: 'Round Linen',  # 108 ROUND PEACH LINEN
    61901: 'Round Linen',  # 108 ROUND CARDINAL RED LINEN
    61904: 'Round Linen',  # 108 ROUND PASTEL PINK LINEN
    61905: 'Round Linen',  # 108 ROUND PINK LINEN
    61908: 'Round Linen',  # 108 ROUND BURGUNDY LINEN
    61910: 'Round Linen',  # 108 ROUND GRAPE (PURPLE) LINEN
    61912: 'Round Linen',  # 108 ROUND EGGPLANT LINEN
    61914: 'Round Linen',  # 108 ROUND AMETHYST LINEN
    61916: 'Round Linen',  # 108 ROUND ROYAL BLUE LINEN
    61921: 'Round Linen',  # 108 ROUND OCEAN BLUE LINEN
    61922: 'Round Linen',  # 108 ROUND PACIFICA LINEN
    61924: 'Round Linen',  # 108 ROUND NAVY BLUE LINEN
    61925: 'Round Linen',  # 108 ROUND CELADON (SAGE) LINEN
    61926: 'Round Linen',  # 108 ROUND HUNTER GREEN LINEN
    61927: 'Round Linen',  # 108 ROUND KELLY GREEN LINEN
    61928: 'Round Linen',  # 108 ROUND LIME GREEN LINEN
    61930: 'Round Linen',  # 120 ROUND  WHITE LINEN
    61931: 'Round Linen',  # 120 ROUND BLACK LINEN
    61933: 'Round Linen',  # 120 ROUND IVORY LINEN
    61934: 'Round Linen',  # 120 ROUND BEIGE LINEN
    61936: 'Round Linen',  # 120 ROUND CHOCOLATE LINEN
    61937: 'Round Linen',  # 120 ROUND LEMON YELLOW LINEN
    61939: 'Round Linen',  # 120 ROUND BYZANTINE FALL GOLD LIN
    61942: 'Round Linen',  # 120 ROUND ORANGE LINEN
    61943: 'Round Linen',  # 120 ROUND SHRIMP LINEN
    61946: 'Round Linen',  # 120 ROUND CARDINAL RED LINEN
    61949: 'Round Linen',  # 120 ROUND PASTEL PINK LINEN
    61950: 'Round Linen',  # 120 ROUND PINK LINEN
    61951: 'Round Linen',  # 120 ROUND MAGENTA LINEN
    61953: 'Round Linen',  # 120 ROUND BURGUNDY LINEN
    61955: 'Round Linen',  # 120 ROUND GRAPE LINEN
    61957: 'Round Linen',  # 120 ROUND EGGPLANT LINEN
    61958: 'Round Linen',  # 120 ROUND AMETHYST LINEN
    61960: 'Round Linen',  # 120 ROUND ROYAL BLUE LINEN
    61961: 'Round Linen',  # 120 ROUND LIGHT BLUE LINEN
    61962: 'Round Linen',  # 120 ROUND MINT LINEN
    61964: 'Round Linen',  # 120 ROUND TURQUOISE LINEN
    61965: 'Round Linen',  # 120 ROUND OCEAN BLUE LINEN
    61967: 'Round Linen',  # 120 ROUND PERIWINKLE LINEN
    61968: 'Round Linen',  # 120 ROUND NAVY BLUE LINEN
    61970: 'Round Linen',  # 120 ROUND HUNTER GREEN LINEN
    61971: 'Round Linen',  # 120 ROUND KELLY GREEN LINEN
    61972: 'Round Linen',  # 120 ROUND LIME GREEN LINEN
    61973: 'Round Linen',  # 120 ROUND DAMASK SOMERSET GOLD LI
    61974: 'Round Linen',  # 120 ROUND ROSE IRIDESCENT CRUSH L
    61975: 'Round Linen',  # 120 ROUND MIDNIGHT BLUE IRIDESCEN
    61976: 'Round Linen',  # 120 ROUND FUCHSIA NOVA SOLID LINE
    61977: 'Round Linen',  # 120 ROUND BERMUDA BLUE NOVA SOLID
    61978: 'Round Linen',  # 120 ROUND APPLE GREEN NOVA SOLID
    61979: 'Round Linen',  # 120 ROUND  WHITE NOVA SWIRL LINEN
    61981: 'Round Linen',  # 132 ROUND  WHITE LINEN
    61982: 'Round Linen',  # 132 ROUND BLACK  LINEN
    61984: 'Round Linen',  # 132 ROUND PEWTER LINEN
    61985: 'Round Linen',  # 132 ROUND IVORY LINEN
    61986: 'Round Linen',  # 132 ROUND BEIGE LINEN
    61989: 'Round Linen',  # 132 ROUND LEMON YELLOW LINEN
    61992: 'Round Linen',  # 132 ROUND POPPY LINEN
    61994: 'Round Linen',  # 132 ROUND ORANGE LINEN
    61996: 'Round Linen',  # 132 ROUND BUBBLEGUM PINK LINEN
    61999: 'Round Linen',  # 132 ROUND CARDINAL RED LINEN
    62003: 'Round Linen',  # 132 ROUND PINK LINEN
    62004: 'Round Linen',  # 132 ROUND MAGENTA LINEN
    62006: 'Round Linen',  # 132 ROUND BURGUNDY LINEN
    62010: 'Round Linen',  # 132 ROUND EGGPLANT LINEN
    62012: 'Round Linen',  # 132 ROUND AMETHYST LINEN
    62014: 'Round Linen',  # 132 ROUND ROYAL BLUE LINEN
    62021: 'Round Linen',  # 132 ROUND PERIWINKLE LINEN
    62022: 'Round Linen',  # 132 ROUND NAVY BLUE LINEN
    62024: 'Round Linen',  # 132 ROUND HUNTER GREEN LINEN
    62025: 'Round Linen',  # 132 ROUND KELLY GREEN LINEN
    62026: 'Round Linen',  # 132 ROUND LIME GREEN LINEN
    62027: 'Round Linen',  # 132 ROUND BURNT ORANGE LINEN
    62028: 'Round Linen',  # 132 ROUND ARMY GREEN LINEN
    62029: 'Round Linen',  # 132 ROUND DAMASK SOMERSET GOLD
    62030: 'Round Linen',  # 132 ROUND DAMASK CAMBRIDGE WHEAT
    62031: 'Round Linen',  # 132 ROUND CHAMPAGNE IRIDESCENT CR
    62032: 'Round Linen',  # 132 ROUND  WHITE SAND IRIDESCENT
    62033: 'Round Linen',  # 132 ROUND SUNSET ORANGE IRD CRUSH
    62034: 'Round Linen',  # 132 ROUND MIDNIGHT BLUE IRIDESCEN
    62035: 'Round Linen',  # 132 ROUND TIFFANY BLUE NOVA SOLID
    72485: 'Round Linen',  # 120 ROUND DUSTY ROSE

    # Rectangle Linen
    
    62037: 'Rectangle Linen',  # LINEN RUNNER 12 X 120  WHITE
    62038: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 BLACK
    62039: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 GREY
    62040: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 PEWTER
    62041: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 IVORY
    62042: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 BEIGE
    62045: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 LEMON YEL
    62054: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 CARDINAL
    62057: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 PASTEL PI
    62065: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 EGGPLANT
    62067: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 AMETHYST
    62077: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 CELADON
    62081: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 TIFFANY B
    62082: 'Rectangle Linen',  # LINEN RUNNER 13 X 120 GOLDENROD
    62083: 'Rectangle Linen',  # LINEN RUNNER 13 X 120 SILVER LA
    62085: 'Rectangle Linen',  # LINEN CAPLET 30X96X10  WHITE SWIRL
    62086: 'Rectangle Linen',  # LINEN CAPLET 30X96X10 SOFT GOLD SW
    62087: 'Rectangle Linen',  # LINEN CAPLET 30X96X10 LAVENDER SWI
    62088: 'Rectangle Linen',  # 60X120  WHITE LINEN
    62089: 'Rectangle Linen',  # 60X120 BLACK LINEN
    62090: 'Rectangle Linen',  # 60X120 GREY LINEN
    62091: 'Rectangle Linen',  # 60X120 PEWTER LINEN
    62092: 'Rectangle Linen',  # 60X120 IVORY LINEN
    62093: 'Rectangle Linen',  # 60X120 BEIGE LINEN
    62094: 'Rectangle Linen',  # 60X120 KHAKI LINEN
    62095: 'Rectangle Linen',  # 60X120 CHOCOLATE LINEN
    62096: 'Rectangle Linen',  # 60X120 LEMON YELLOW LINEN
    62098: 'Rectangle Linen',  # 60X120 BYZANTINE FALL GOLD LINEN
    62099: 'Rectangle Linen',  # 60X120 POPPY LINEN
    62101: 'Rectangle Linen',  # 60X120 ORANGE LINEN
    62102: 'Rectangle Linen',  # 60X120 SHRIMP LINEN
    62103: 'Rectangle Linen',  # 60X120 BUBBLEGUM PINK LINEN
    62104: 'Rectangle Linen',  # 60X120 RED LINEN
    62106: 'Rectangle Linen',  # 60X120 CARDINAL RED LINEN
    62107: 'Rectangle Linen',  # 60X120 HOT PINK LINEN
    62111: 'Rectangle Linen',  # 60X120 PINK LINEN
    62112: 'Rectangle Linen',  # 60X120 MAGENTA LINEN
    62113: 'Rectangle Linen',  # 60X120 FLAMINGO LINEN
    62114: 'Rectangle Linen',  # 60X120 BURGUNDY LINEN
    62116: 'Rectangle Linen',  # 60X120 GRAPE LINEN
    62117: 'Rectangle Linen',  # 60X120 PLUM LINEN
    62118: 'Rectangle Linen',  # 60X120 EGGPLANT LINEN
    62119: 'Rectangle Linen',  # 60X120 AMETHYST LINEN
    62121: 'Rectangle Linen',  # 60X120 ROYAL BLUE LINEN
    62122: 'Rectangle Linen',  # 60X120 LIGHT BLUE LINEN
    62126: 'Rectangle Linen',  # 60X120 OCEAN BLUE LINEN
    62129: 'Rectangle Linen',  # 60X120 NAVY BLUE LINEN
    62130: 'Rectangle Linen',  # 60X120 CELADON LINEN
    62131: 'Rectangle Linen',  # 60X120 HUNTER GREEN LINEN
    62132: 'Rectangle Linen',  # 60X120 KELLY GREEN LINEN
    62133: 'Rectangle Linen',  # 60X120 LIME GREEN LINEN
    62134: 'Rectangle Linen',  # 60X120 BLUE GINGHAM LINEN
    62136: 'Rectangle Linen',  # 60X120 ROSE IRIDESCENT CRUSH LINEN
    62137: 'Rectangle Linen',  # 60X120 VIOLET GREEN IRIDESCENT CRU
    62138: 'Rectangle Linen',  # 60X120 TIFFANY BLUE NOVA SOLID LIN
    62139: 'Rectangle Linen',  # 60X120 SOFT SAGE NOVA SOLID LINEN
    62140: 'Rectangle Linen',  # 60X120 CANDY PINK NOVA SWIRL LINEN
    62141: 'Rectangle Linen',  # 60X120 BAMBOO NOVA SWIRL LINEN
    62142: 'Rectangle Linen',  # 60X120 SILVER LAME
    62187: 'Rectangle Linen',  # 90X132  WHITE LINEN ROUNDED CORNE
    62188: 'Rectangle Linen',  # 90X132 BLACK LINEN ROUNDED CORNER
    62189: 'Rectangle Linen',  # 90X132 GREY LINEN ROUNDED CORNERS
    62191: 'Rectangle Linen',  # 90X132 IVORY LINEN ROUNDED CORNER
    62194: 'Rectangle Linen',  # 90X132 CHOCOLATE LINEN ROUNDED CO
    62198: 'Rectangle Linen',  # 90X132 POPPY LINEN ROUNDED CORNER
    62204: 'Rectangle Linen',  # 90X132 CARDINAL RED LINEN ROUNDED
    62208: 'Rectangle Linen',  # 90X132 PINK LINEN ROUNDED CORNERS
    62211: 'Rectangle Linen',  # 90X132 BURGUNDY LINEN ROUNDED COR
    62214: 'Rectangle Linen',  # 90X132 PLUM LINEN ROUNDED CORNERS
    62215: 'Rectangle Linen',  # 90X132 EGGPLANT LINEN ROUNDED COR
    62219: 'Rectangle Linen',  # 90X132 ROYAL BLUE LINEN ROUNDED C
    62224: 'Rectangle Linen',  # 90X132 OCEAN LINEN ROUNDED CORNER
    62225: 'Rectangle Linen',  # 90X132 PACIFICA LINEN ROUNDED COR
    62226: 'Rectangle Linen',  # 90X132 PERIWINKLE LINEN ROUNDED C
    62227: 'Rectangle Linen',  # 90X132 NAVY BLUE LINEN ROUNDED CO
    62229: 'Rectangle Linen',  # 90X132 HUNTER GREEN LINEN ROUNDED
    62232: 'Rectangle Linen',  # 90X132 MIDNIGHT BLUE IRD CRUSH RO
    62235: 'Rectangle Linen',  # 90X156  WHITE LINEN ROUNDED CORNE
    62236: 'Rectangle Linen',  # 90X156 BLACK LINEN ROUNDED CORNER
    62237: 'Rectangle Linen',  # 90X156 GREY LINEN ROUNDED CORNERS
    62238: 'Rectangle Linen',  # 90X156 PEWTER LINEN ROUNDED CORNE
    62239: 'Rectangle Linen',  # 90X156 IVORY LINEN ROUNDED CORNER
    62242: 'Rectangle Linen',  # 90X156 CHOCOLATE LINEN ROUNDED CO
    62246: 'Rectangle Linen',  # 90X156 POPPY LINEN ROUNDED CORNER
    62247: 'Rectangle Linen',  # 90X156 PEACH LINEN ROUNDED CORNER
    62252: 'Rectangle Linen',  # 90X156 CARDINAL RED LINEN ROUNDED
    62255: 'Rectangle Linen',  # 90X156 PASTEL PINK LINEN ROUNDED
    62256: 'Rectangle Linen',  # 90X156 PINK LINEN ROUNDED CORNERS
    62257: 'Rectangle Linen',  # 90X156 MAGENTA LINEN ROUNDED CORN
    62263: 'Rectangle Linen',  # 90X156 EGGPLANT LINEN ROUNDED COR
    62265: 'Rectangle Linen',  # 90X156 AMETHYST LINEN ROUNDED COR
    62267: 'Rectangle Linen',  # 90X156 ROYAL BLUE LINEN ROUNDED C
    62268: 'Rectangle Linen',  # 90X156 LIGHT BLUE LINEN ROUNDED C
    62271: 'Rectangle Linen',  # 90X156 TURQUOISE LINEN ROUNDED CO
    62272: 'Rectangle Linen',  # 90X156 OCEAN LINEN ROUNDED CORNER
    62273: 'Rectangle Linen',  # 90X156 PACIFICA LINEN ROUNDED COR
    62274: 'Rectangle Linen',  # 90X156 PERIWINKLE LINEN ROUNDED C
    62275: 'Rectangle Linen',  # 90X156 NAVY BLUE LINEN ROUNDED CO
    62277: 'Rectangle Linen',  # 90X156 HUNTER GREEN LINEN ROUNDED
    62280: 'Rectangle Linen',  # 90X156 DAMASK SOMERSET GOLD LINEN
    62281: 'Rectangle Linen',  # 90X156 PLATINUM IRIDESCENT CRUSH L
    62282: 'Rectangle Linen',  # 90X156 CHAMPAGNE IRIDESCENT CRUSH
    62283: 'Rectangle Linen',  # 90X156 MIDNIGHT BLUE IRIDESCENT CR
    62287: 'Rectangle Linen',  # 30X96 CONFERENCE LINEN  WHITE
    62288: 'Rectangle Linen',  # 30X96 CONFERENCE LINEN BLACK
    62289: 'Rectangle Linen',  # 30X96 CONFERENCE LINEN EGGPLANT
    62290: 'Rectangle Linen',  # LINEN SERPENTINE FITTED 4 WHITE
    62291: 'Rectangle Linen',  # 54 SQUARE  WHITE LINEN
    62292: 'Rectangle Linen',  # 54 SQUARE BLACK LINEN
    62294: 'Rectangle Linen',  # 54 SQUARE PEWTER LINEN
    62295: 'Rectangle Linen',  # 54 SQUARE IVORY LINEN
    62298: 'Rectangle Linen',  # 54 SQUARE CHOCOLATE LINEN
    62308: 'Rectangle Linen',  # 54 SQUARE CARDINAL RED
    62312: 'Rectangle Linen',  # 54 SQUARE PINK LINEN
    62315: 'Rectangle Linen',  # 54 SQUARE BURGUNDY LINEN
    62319: 'Rectangle Linen',  # 54 SQUARE EGGPLANT LINEN
    62321: 'Rectangle Linen',  # 54 SQUARE AMETHYST LINEN
    62323: 'Rectangle Linen',  # 54 SQUARE ROYAL BLUE  LINEN
    62330: 'Rectangle Linen',  # 54 SQUARE PERIWINKLE LINEN
    62331: 'Rectangle Linen',  # 54 SQUARE NAVY BLUE LINEN
    62332: 'Rectangle Linen',  # 54 SQUARE CELADON LINEN
    62333: 'Rectangle Linen',  # 54 SQUARE HUNTER GREEN LINEN
    62336: 'Rectangle Linen',  # 54 SQUARE ARMY GREEN LINEN
    62337: 'Rectangle Linen',  # 54 SQUARE BURLAP (PRAIRIE) LINEN
    62338: 'Rectangle Linen',  # 54 SQUARE SILVER LAME  LINEN
    62339: 'Rectangle Linen',  # 72 SQUARE BURLAP (PRAIRIE) LINEN
    62399: 'Rectangle Linen',  # 90X90  WHITE LINEN
    62401: 'Rectangle Linen',  # 90X90 GREY LINEN
    62403: 'Rectangle Linen',  # 90X90 IVORY LINEN
    62426: 'Rectangle Linen',  # 90X90 PLUM LINEN
    65545: 'Rectangle Linen',  # LINEN RUNNER 12 X 120 RED CHECK
    # Concession
    2857: 'Concession Equipment',  # "FOUNTAIN, CHOCOLATE"
    3290: 'Concession Equipment',  # "BEVERAGE COOLER, 5 GAL CAMBRO THERMOVAT"
    3727: 'Concession Equipment',  # HOTDOG STEAMER
    3902: 'Concession Equipment',  # NACHO CHEESE DISPENSER and WARMER
    62468: 'Concession Equipment',  # "BEVERAGE COOLER, 10 GAL CAMBRO THERMOVAT"
    62475: 'Concession Equipment',  # "BEVERAGE DISPENSER, CLEAR-IVORY 5 GAL"
    62479: 'Concession Equipment',  # "BEVERAGE DISPENSER, CLEAR 5 GAL w/INFUSE"
    62535: 'Concession Equipment',  # "HOTDOG MACH, ROLLER (CAPACITY 50) 12AMP"
    62633: 'Concession Equipment',  # "CHAFER, FULLSIZE, STAINLESS (GOLD TRIM)"
    62634: 'Concession Equipment',  # "CHAFER, FULLSIZE, STAINLESS STEEL"
    62636: 'Concession Equipment',  # "CHAFER, FULLSIZE, ROLLTOP, STAINLESS 8QT"
    62637: 'Concession Equipment',  # "CHAFER, HALFSIZE, STAINLESS STEEL"
    62651: 'Concession Equipment',  # "FOUNTAIN, 3 GAL PRINCESS (6AMP)"
    62652: 'Concession Equipment',  # "FOUNTAIN, 7 GAL PRINCESS (6 AMP)"
    62653: 'Concession Equipment',  # "FOUNTAIN, 4 1/2 GAL EMPRESS (6 AMP)"
    62654: 'Concession Equipment',  # "FOUNTAIN, 3 GAL EMPRESS (6 AMP)"
    63791: 'Concession Equipment',  # "WARMER 3-1/2 QT, ELECTRIC (5amp, 120v)"
    63793: 'Concession Equipment',  # "WARMER 3-1/2 QT, ELECTRIC (HEATED STEM)"
    63806: 'Concession Equipment',  # FROZEN DRINK MACHINE -SINGLE BARREL
    66715: 'Concession Equipment',  # MINI DONUT MACHINE
    68317: 'Concession Equipment',  # FROZEN DRINK MACHINE - OTC (6 AMP)
    68318: 'Concession Equipment',  # "POPCORN MACHINE, 8 oz DELV CASE"
    68320: 'Concession Equipment',  # "POPCORN MACHINE, 8 OZ,10AMP, TABLETOP"
    68321: 'Concession Equipment',  # "SNO-KONE MACHINE, 7 AMP ELECTRIC"
    68322: 'Concession Equipment',  # "COTTON CANDY MACHINE, 9 AMP 120V"
    68332: 'Concession Equipment',  # FROZEN DRINK MACHINE -DOUBLE BARREL

    # RUNNERS AND DRAPES
    63278: 'Runners and Drapes',  # "DRAPES, BLACK 16 X 48 (ADJ 10,12,16)"
    63295: 'Runners and Drapes',  # "DRAPES, BLACK  3 X 48 BANJO"
    63296: 'Runners and Drapes',  # "DRAPES, SILVER 3 X 48 BANJO"
    63297: 'Runners and Drapes',  # "DRAPES, BLUE 3 X 48 BANJO"
    63298: 'Runners and Drapes',  # "DRAPES, WHITE -ARCTIC SNOW,  8X 4"
    63299: 'Runners and Drapes',  # "DRAPES, BLACK  8 X 58 VELOUR"
    63300: 'Runners and Drapes',  # "DRAPES, BLACK  8 X 48 BANJO"
    63301: 'Runners and Drapes',  # "DRAPES, SILVER 8 X 48 BANJO"
    63302: 'Runners and Drapes',  # "DRAPES, CHARCOAL, 8 X 48 BANJO"
    63303: 'Runners and Drapes',  # "DRAPES, IVORY, 8 X 48 BANJO"
    63304: 'Runners and Drapes',  # "DRAPES, GOLD, 8 X 48 BANJO"
    63305: 'Runners and Drapes',  # "DRAPES, ORANGE, 8 X 48 BANJO"
    63306: 'Runners and Drapes',  # "DRAPES, RED, 8 X 48 BANJO"
    63307: 'Runners and Drapes',  # "DRAPES, BURGUNDY 8 X 48 BANJO"
    63308: 'Runners and Drapes',  # "DRAPES, RASPBERRY, 8 X 48 BANJO"
    63309: 'Runners and Drapes',  # "DRAPES, PURPLE, 8 X 48 BANJO"
    63310: 'Runners and Drapes',  # "DRAPES, BLUE 8 X 48 BANJO"
    63311: 'Runners and Drapes',  # "DRAPES, WHITE -SHEER  8H X 118W"
    63313: 'Runners and Drapes',  # "DRAPES, NAVY BLUE, 8 X 48 BANJO"
    63314: 'Runners and Drapes',  # "DRAPES, FOREST GREEN 8 X 48 BANJO"
    63315: 'Runners and Drapes',  # "DRAPES, HUNTER GREEN 8 X 48 BANJO"
    63316: 'Runners and Drapes',  # "DRAPES, BLACK 16 X 48 BANJO"
    63317: 'Runners and Drapes',  # "DRAPES, WHITE -SHEER 16H X 118W"
    63327: 'Runners and Drapes',  # "CARPET RUNNER, RED 4 X 25 (G1)"
    63328: 'Runners and Drapes',  # "CARPET RUNNER, RED 4 X 25 (G2)"
    63329: 'Runners and Drapes',  # "CARPET RUNNER, RED 4 X 50 (G1)"
    63330: 'Runners and Drapes',  # "CARPET RUNNER, RED 4 X 50 (G2)"
    63331: 'Runners and Drapes',  # "CARPET RUNNER, PURPLE 4 X 25"
    63332: 'Runners and Drapes',  # "CARPET RUNNER, PURPLE 4 X 50 (G1)"
    64836: 'Runners and Drapes',  # AISLE CLOTH 75 WHITE
    64837: 'Runners and Drapes',  # AISLE CLOTH 100 WHITE
    66688: 'Runners and Drapes',  # "DRAPES, BLACK  8 X 48 POLY"

    # OTHER

    61749: 'Other',  # BAG FOR SOILED LINEN
    61750: 'Other',  # SKIRT STAGE 24 X 13 BLACK BAN
    61758: 'Other',  # SKIRT STAGE 44 X 13 BLACK BAN
    61759: 'Other',  # SKIRT 8 WHITE (30)
    61760: 'Other',  # SKIRT  8 BLACK (30)
    61761: 'Other',  # SKIRT 14  WHITE (30)
    61762: 'Other',  # SKIRT 14 BLACK (30)
    61763: 'Other',  # SKIRT 14 IVORY (30)
    61764: 'Other',  # SKIRT 21 WHITE (30)
    62445: 'Other',  # SPANDEX LINEN  WHITE 30 X 42 (W/BLK F
    62447: 'Other',  # SPANDEX LINEN BLACK 30x42 (COCKTAIL)
    62449: 'Other',  # SPANDEX ICE TABLE SKIRT BLACK (SMALL)
    62451: 'Other',  # SPANDEX ICE TABLE SKIRT WHITE (LARGE)
    62452: 'Other',  # SPANDEX ICE TABLE SKIRT BLACK (LARGE)
    62233: 'Other',  # SPANDEX TABLE LINEN  WHITE 6X30 BANQ
    62234: 'Other',  # SPANDEX TABLE LINEN BLACK 6X30 BANQ
    62284: 'Other',  # SPANDEX TABLE LINEN  WHITE 8X30 BANQ
    62285: 'Other',  # SPANDEX TABLE LINEN BLACK 8X30 BANQ
    67139: 'Other',  # SPANDEX LINEN  WHITE 36 X 42
    67140: 'Other',  # SPANDEX LINEN  BLACK 36 X 42
    99999: 'Other',  # HP 15x15 IKEs Bar

    # Resale

    1: 'Resale',  # test resale
    3168: 'Resale',  # CHOCOLATE BAG 2LB. DARK
    3169: 'Resale',  # CHOCOLATE BAG 2LB. MILK
    3903: 'Resale',  # NACHO CHEESE 140oz BAG
    64815: 'Resale',  # FOG SOLUTION (GROUND) 1 QUART
    64816: 'Resale',  # FOG SOLUTION (HAZE) 1 QUART
    64817: 'Resale',  # BUBBLE JUICE 1 QUART
    64819: 'Resale',  # FUEL STERNO 8 OZ -LASTS 2+HRS
    64824: 'Resale',  # FUEL BUTANE CARTRIDGE 8 OUNCE
    64840: 'Resale',  # COTTON CANDY SUGAR PINK VANILLA (52 OZ
    64841: 'Resale',  # COTTON CANDY SUGAR BLUE RASPBERRY-52oz
    64842: 'Resale',  # COTTON CANDY SUGAR CHERRY (52 OZ CARTON
    64843: 'Resale',  # COTTON CANDY SUGAR STRAWBERRY (52 OZ CA
    64847: 'Resale',  # COTTON CANDY BAGS & TIES 100 PER PKG
    64848: 'Resale',  # COTTON CANDY CONES 100 PER PKG.
    64849: 'Resale',  # COTTON CANDY SUGAR BUBBLE GUM (52 OZ CA
    64852: 'Resale',  # POPCORN/SALT/OIL PRE-MEASURED KIT
    64853: 'Resale',  # POPCORN BAGS 50/ PKG
    64854: 'Resale',  # NACHO CHEESE SAUCE #10 CAN
    64855: 'Resale',  # SNOKONE SYRUP **LIME** 1 GALLON
    64856: 'Resale',  # SNOKONE SYRUP **GRAPE** 1 GALLON
    64857: 'Resale',  # SNOKONE SYRUP **CHERRY** 1 GALLON
    64858: 'Resale',  # SNOKONE SYRUP **BLUE RASPBERRY 1 GALLON
    64860: 'Resale',  # SNOKONE KONES 200 COUNT BOX
    64861: 'Resale',  # SNOKONE SYRUP PUMP (1 GAL)
    64864: 'Resale',  # FRUSHEEZE STRAWBERRY DAQ 1/2 GALLON
    64865: 'Resale',  # FRUSHEEZE FRUIT PUNCH 1/2 GALLON
    64866: 'Resale',  # FRUSHEEZE MARGARITA 1/2 GALLON
    64867: 'Resale',  # FRUSHEEZE BLUE RASPBERRY 1/2 GALLON
    64868: 'Resale',  # FRUSHEEZE PINA COLADA 1/2 GALLON
    64869: 'Resale',  # FRUSHEEZE CHERRY 1/2 GALLON
    64874: 'Resale',  # FRUSHEEZE LEMONADE GRANITA MIX 1 GAL (5
    64876: 'Resale',  # GARBAGE CAN DISPOSABLE 35 GAL W/ LID
    64888: 'Resale',  # KWIK COVER WHITE ROUND 30 PLASTIC
    64889: 'Resale',  # KWIK COVER BLACK ROUND 30 PLASTIC
    64890: 'Resale',  # KWIK COVER RED ROUND 30 PLASTIC
    64891: 'Resale',  # KWIK COVER GINGHAM RED ROUND 30 PLASTI
    64892: 'Resale',  # KWIK COVER ROYAL BLUE ROUND 30
    64893: 'Resale',  # KWIK COVER HUNTER GREEN ROUND 30 PLAST
    64894: 'Resale',  # KWIK COVER WHITE ROUND 48 PLASTIC
    64895: 'Resale',  # KWIK COVER BLACK ROUND 48 PLASTIC
    64896: 'Resale',  # KWIK COVER SUNSHINE GOLD ROUND 48 PLAS
    64897: 'Resale',  # KWIK COVER ORANGE ROUND 48 PLASTIC
    64898: 'Resale',  # KWIK COVER RED ROUND 48 PLASTIC
    64899: 'Resale',  # KWIK COVER GINGHAM RED ROUND 48 PLASTI
    64900: 'Resale',  # KWIK COVER MAROON ROUND 48 PLASTIC
    64901: 'Resale',  # KWIK COVER PURPLE ROUND 48 PLASTIC
    64902: 'Resale',  # KWIK COVER ROYAL BLUE ROUND 48 PLASTIC
    64904: 'Resale',  # KWIK COVER HUNTER GREEN ROUND 48 PLAST
    64905: 'Resale',  # KWIK COVER BLACK & WHITE CHECK ROUND 48
    64906: 'Resale',  # KWIK COVER WHITE ROUND 60 PLASTIC
    64907: 'Resale',  # KWIK COVER BLACK ROUND 60 PLASTIC
    64908: 'Resale',  # KWIK COVER SUNSHINE GOLD ROUND 60 PLAS
    64909: 'Resale',  # KWIK COVER ORANGE ROUND 60 PLASTIC
    64910: 'Resale',  # KWIK COVER RED ROUND 60 PLASTIC
    64911: 'Resale',  # KWIK COVER GINGHAM RED ROUND 60 PLASTI
    64912: 'Resale',  # KWIK COVER PINK ROUND 60 PLASTIC
    64913: 'Resale',  # KWIK COVER MAROON ROUND 60 PLASTIC
    64914: 'Resale',  # KWIK COVER PURPLE ROUND 60 PLASTIC
    64915: 'Resale',  # KWIK COVER ROYAL BLUE ROUND 60 PLASTIC
    64916: 'Resale',  # KWIK COVER LIGHT BLUE ROUND 60 PLASTIC
    64917: 'Resale',  # KWIK COVER GINGHAM BLUE ROUND 60 PLAST
    64918: 'Resale',  # KWIK COVER HUNTER GREEN ROUND 60 PLAST
    64919: 'Resale',  # KWIK COVER LIME GREEN ROUND 60 PLASTIC
    64920: 'Resale',  # KWIK COVER BLACK & WHITE CHECK ROUND 60
    64921: 'Resale',  # KWIK COVER WHITE 6 X 30 PLASTIC
    64922: 'Resale',  # KWIK COVER BLACK 6 X 30 PLASTIC
    64923: 'Resale',  # KWIK COVER SUNSHINE GOLD 6 X 30 PLAST
    64924: 'Resale',  # KWIK COVER ORANGE 6 X 30 PLASTIC
    64925: 'Resale',  # KWIK COVER RED 6 X 30 PLASTIC
    64926: 'Resale',  # KWIK COVER GINGHAM RED 6 X 30 PLASTIC
    64927: 'Resale',  # KWIK COVER PINK 6 X 30 PLASTIC
    64928: 'Resale',  # KWIK COVER MAROON 6 X 30 PLASTIC
    64929: 'Resale',  # KWIK COVER PURPLE 6 X 30 PLASTIC
    64930: 'Resale',  # KWIK COVER ROYAL BLUE 6 X 30 PLASTIC
    64932: 'Resale',  # KWIK COVER HUNTER GREEN 6 X 30 PLASTI
    64933: 'Resale',  # KWIK COVER LIME GREEN 6 X 30 PLASTIC
    64934: 'Resale',  # KWIK COVER BLACK & WHITE CHECK 6 X 30
    64935: 'Resale',  # KWIK COVER WHITE 8 X 30 PLASTIC
    64936: 'Resale',  # KWIK COVER BLACK 8 X 30 PLASTIC
    64937: 'Resale',  # KWIK COVER SUNSHINE GOLD 8 X 30 PLAST
    64938: 'Resale',  # KWIK COVER ORANGE 8 X 30 PLASTIC
    64939: 'Resale',  # KWIK COVER RED 8 X 30 PLASTIC
    64940: 'Resale',  # KWIK COVER GINGHAM RED 8 X 30 PLASTIC
    64941: 'Resale',  # KWIK COVER PINK 8 X 30 PLASTIC
    64942: 'Resale',  # KWIK COVER MAROON 8 X 30 PLASTIC
    64943: 'Resale',  # KWIK COVER PURPLE 8 X 30 PLASTIC
    64944: 'Resale',  # KWIK COVER ROYAL BLUE 8 X 30 PLASTIC
    64945: 'Resale',  # KWIK COVER LIGHT BLUE 8 X 30 PLASTIC
    64946: 'Resale',  # KWIK COVER GINGHAM BLUE 8 X 30
    64947: 'Resale',  # KWIK COVER HUNTER GREEN 8 X 30 PLASTI
    64948: 'Resale',  # KWIK COVER LIME GREEN 8 X 30 PLASTIC
    64949: 'Resale',  # KWIK COVER BLACK & WHITE CHECK 8 X 30
    65493: 'Resale',  # KWIK COVER SILVER 6 x 30 BANQ
    65494: 'Resale',  # KWIK COVER SILVER 8 x 30 BANQ
    65495: 'Resale',  # KWIK COVER SILVER 60 ROUND
    65496: 'Resale',  # KWIK COVER NAVY BLUE 6 x 30 BANQ
    65497: 'Resale',  # KWIK COVER NAVY BLUE 8 x 30 BANQ
    65498: 'Resale',  # KWIK COVER NAVY BLUE 60 ROUND
    65604: 'Resale',  # KWIK COVER BLACK ROUND 36
    65605: 'Resale',  # KWIK COVER WHITE ROUND 36
    65606: 'Resale',  # KWIK COVER HUNTER GREEN ROUND 36
    65607: 'Resale',  # KWIK COVER ROYAL BLUE ROUND 36
    65608: 'Resale',  # KWIK COVER RED ROUND 36
    65609: 'Resale',  # KWIK COVER GINGHAM RED ROUND 36
    65611: 'Resale',  # KWIK COVER WHITE 4 x 30 BANQ
    65808: 'Resale',  # SNOKONE SYRUP **PINK LEMONADE** 1 GALLON
    63442: 'Resale',  # KWIK COVER GINGHAM BLUE 6 X 30
    63440: 'Resale',  # KWIK COVER GINGHAM BLUE ROUND 48
    66742: 'Resale',  # DONUT BAGS-MINI 70ct
    66743: 'Resale',  # DONUT SUGAR 5 LBS & DISPENSER
    66747: 'Resale',  # MINI DONUT -70 SERVINGS- SUPPLY PACKAGE
}

SUBCATEGORY_MAP = {
    # Tent Tops
    4052: 'HP Sidewalls',  # SIDEWALL HP 10 x 8 WHITE
    4054: 'HP 20x Tops',  # Canopy 20x20 HP TOP SKYLIGHT
    4203: 'Navi Lite Tops',  # TOP NAVI LITE 30x15 HIP G1
    4204: 'Navi Lite Tops',  # TOP NAVI LITE 30x15 MID G1
    4213: 'Navi Sidewalls',  # SIDEWALL NAVI LITE 8x 15 WINDOW KEDAR
    4214: 'Navi Sidewalls',  # SIDEWALL NAVI LITE 8 x 15 WHITE KEDAR
    4292: 'HP 20x Tops',  # Canopy 20x30 HP TOP WHITE Single Peak
    4807: 'HP Sidewalls',  # SIDEWALL HP 15 x 9 WINDOW (G1)
    4808: 'HP Sidewalls',  # SIDEWALL HP 15 x 9 WHITE (G1)
    60526: 'Navi Sidewalls',  # SIDEWALL KEDARNAVI 15x8 (G1) WINDOW
    60528: 'Navi Sidewalls',  # SIDEWALL KEDAR NAVI 15x8 (G1) WHITE
    65119: 'HP Tops', #G1

    62706: 'HP Tops',  # TOP HP 10 X 10 (G1)
    62707: 'HP Tops',  # TOP HP 10 X 20 (G2)
    62708: 'HP Tops',  # TOP HP 15X15 (G1)
    62709: 'HP Tops',  # TOP HP 20 X 20 (G2)
    62711: 'HP Tops',  # TOP HP 30 X 30 (G1)
    62714: 'HP Tops',  # TOP HP HEX 35 X 40 WHITE
    62715: 'HP Sidewalls',  # SIDEWALL HP 15 x 8 (G1) WINDOW
    62719: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G1) w/DOOR/WIND
    62723: 'HP Sidewalls',  # SIDEWALL HP 10 x 8 (G1) WINDOW
    62727: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G1) WINDOW
    62731: 'HP Sidewalls',  # SIDEWALL HP 30 x 8 (G1) WINDOW
    62735: 'HP Sidewalls',  # SIDEWALL HP 20 x 9 (G1) WINDOW
    62737: 'HP Sidewalls',  # SIDEWALL HP 20 x 9 (G3) WINDOW
    62745: 'HP Sidewalls',  # SIDEWALL HP 15 x 8 (G1) w/DOOR
    62749: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G1) w/DOOR pole
    62750: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G2) w/DOOR pole
    62753: 'HP Sidewalls',  # SIDEWALL HP 10 x 8 (G1) WHITE
    62755: 'HP Sidewalls',  # SIDEWALL HP 10 x 8 (G3) WHITE
    62757: 'HP Sidewalls',  # SIDEWALL HP 15 x 8 (G1) WHITE
    62761: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G1) WHITE
    62762: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G2) WHITE
    62763: 'HP Sidewalls',  # SIDEWALL HP 20 x 8 (G3) WHITE
    62769: 'HP Sidewalls',  # SIDEWALL HP 20 x 9 (G1) WHITE
    62770: 'HP Sidewalls',  # SIDEWALL HP 20 x 9 (G2) WHITE
    62773: 'HP Sidewalls',  # SIDEWALL HP 20 x 7 (G1) WHITE
    62781: 'HP Sidewalls',  # SIDEWALL HP 30 x 8 (G1) WHITE pole
    62782: 'HP Sidewalls',  # SIDEWALL HP 30 x 8 (G2) WHITE pole
    62805: 'Navi Tops',  # TOP NAVI 30x15 MID (G1)
    62806: 'Pole Tops',  # MID 30 x 15 (G1) R AND W POLE CMATE
    62807: 'Pole Tops',  # END 30 x 15 LACE (G1) R AND W POLE
    62808: 'Navi Tops',  # TOP NAVI 30x15 HIP
    62809: 'Pole 40x & 60x Tops',  # MID 60 x 20 ANCHOR POLE NC (G1)
    62810: 'Pole 40x & 60x Tops',  # MID 60 x 30 (G1) ANCHOR POLE NC
    62853: 'STD Sidewalls',  # SIDEWALLMESH 7 H X 20 (G1) WH
    62857: 'STD Sidewalls',  # SIDEWALL STD 7 X 20 (G1) WINDOW
    62858: 'STD Sidewalls',  # SIDEWALL STD 7 X 20 (G2) WINDOW
    62859: 'STD Sidewalls',  # SIDEWALL STD 7 X 20 (G3) WINDOW
    62861: 'STD Sidewalls',  # SIDEWALL STD 7 X 30 (G1) WINDOW
    62862: 'STD Sidewalls',  # SIDEWALL STD 7 X 30 (G2) WINDOW
    62864: 'STD Sidewalls',  # SIDEWALL STD 7 X 40 (G1) WINDOW
    62865: 'STD Sidewalls',  # SIDEWALL STD 7 X 40 (G2) WINDOW
    62867: 'STD Sidewalls',  # SIDEWALL STD 8 X 20 (G1) WINDOW
    62868: 'STD Sidewalls',  # SIDEWALL STD 8 X 20 (G2) WINDOW
    62871: 'Navi Sidewalls',  # SIDEWALL NAVI 8 X 30 (G1) WINDOW
    62872: 'Navi Sidewalls',  # SIDEWALL NAVI 8 X 30 (G2) WINDOW
    62875: 'STD Sidewalls',  # SIDEWALL STD 8 X 40 (G1) WINDOW
    62876: 'STD Sidewalls',  # SIDEWALL STD 8 X 40 (G2) WINDOW
    62883: 'STD Sidewalls',  # SIDEWALLEXTENDER 3 X 20 (G2)
    62887: 'STD Sidewalls',  # SIDEWALLEXTENDER 3 X 30 (G2)
    62891: 'STD Sidewalls',  # SIDEWALLEXTENDER 3 X 40 (G2)
    62894: 'STD Sidewalls',  # SIDEWALL STD 7 X 20 (G1) WHITE
    62895: 'STD Sidewalls',  # SIDEWALL STD 7 X 20 (G2) WHITE
    62896: 'STD Sidewalls',  # SIDEWALL STD 7 X 20 (G3) WHITE
    62797: 'Pole 40x & 60x Tops',  # MID 40 x 20 (G1) NCP
    62798: 'Pole 40x & 60x Tops',  # END 40 x 20 LACE (G1) NCP
    62900: 'STD Sidewalls',  # SIDEWALL STD 8 X 20 (G1) WHITE
    62901: 'STD Sidewalls',  # SIDEWALL STD 8 X 20 (G2) WHITE
    62902: 'STD Sidewalls',  # SIDEWALL STD 8 X 20 (G3) WHITE
    62904: 'Navi Sidewalls',  # SIDEWALL NAVI 8 X 30 (G1) WHITE
    62905: 'Navi Sidewalls',  # SIDEWALL NAVI 8 X 30 (G2) WHITE
    62906: 'Navi Sidewalls',  # SIDEWALL NAVI 8 X 30 (G3) WHITE
    65035: 'Pole 40x & 60x Tops',  # END 40 x 20 GRMT (G1) ANCHOR POLE NC
    65036: 'Pole 40x & 60x Tops',  # END 60 x 20 LACE (G1) ANCHOR POLE NC
    65037: 'Pole 40x & 60x Tops',  # END 30 x 15 GRMT (G1) R AND W POLE
    65367: 'HP Tops',  # TOP HP 20 X 20 (G1)
    65446: 'HP Tops',  # TOP HP HEX 35 X 40 SKYLIGHT
    65449: 'Navi Gable Tops',  # TOP NAVI 15 GABLE ENDCAP LACE
    65450: 'Navi Gable Tops',  # TOP NAVI 15 GABLE ENDCAP GRMT
    65467: 'Navi Gable Tops',  # TOP NAVI 20 GABLE ENDCAP GRMT
    65468: 'Navi Gable Tops',  # TOP NAVI 20 GABLE ENDCAP LACE
    65469: 'Navi 40x Tops',  # TOP NAVI 40x15 MID (G1)
    66324: 'Navi Lite Tops',  # TOP NAVI LITE 30x15 MID G2
    66325: 'Navi Tops',  # TOP NAVI 30x15 MID (G2)
    66326: 'Navi Tops',  # TOPS NAVI 30x15 MID
    67657: 'HP Tops',  # TOP HP 20 X 30 (G1) WHITE DBL PEAK
    65129: 'POPUP Tents',  # CANOPY 10X10 POPUP WHITE WEIGHTED
    66363: 'APC Tents',  # CANOPY AP 16X16 WHITE (R)(G1)
    72252: 'Navi Sidewalls',  # SIDEWALL KEDAR -G 8' x 5' PANEL
    72253: 'Navi Sidewalls',  # SIDEWALL KEDAR -R 8' x 5' PANEL
    72392: 'Navi Lite Tops',  # TOP NAVI LITE 30x15 HIP G2
    72401: 'HP Crates',  # "CRATE, HP 10 x 10 ASSEMBLY"
    72402: 'HP Crates',  # "CRATE, HP 15 x 15 ASSEMBLY"
    72403: 'HP Crates',  # "CRATE, HP 10 x 20 ASSEMBLY"
    72404: 'HP Crates',  # "CRATE, HP 20 x 20 ASSEMBLY"
    72405: 'HP Crates',  # "CRATE, HP 30 x 30 ASSEMBLY"
    72406: 'HP Crates',  # "CRATE, HP HEX 35 x 40 ASSEMBLY"
    72407: 'HP Crates',  # "CRATE, HP 20 x 30 ASSEMBLY"
    72408: 'Navi Crates',  # "CRATE, NAVI HIP ASSEMBLY"
    72409: 'Navi Crates',  # "CRATE, NAVI MID ASSEMBLY"
    72410: 'Navi Crates',  # "CRATE, NAVI LITE HIP ASSEMBLY"
    72411: 'Navi Crates',  # "CRATE, NAVI LITE MID ASSEMBLY"
    72412: 'Navi Crates',  # "CRATE, NAVI INSTALLATION"
    62668: 'APC Tents',  # CANOPY AP 20X20 WHITE (Rope)(G1)
    62669: 'APC Tents',  # CANOPY AP 20X20 WHITE (Rope)(G2)
    62681: 'APC Tents',  # CANOPY AP 20X30 WHITE (Rope)(G2)
    62682: 'APC Tents',  # CANOPY AP 20X30 WHITE (Rope)(G1)
    62683: 'APC Tents',  # CANOPY AP 20X40 WHITE (Rope)(G1)
    62684: 'APC Tents',  # CANOPY AP 20X40 WHITE (Rope)(G2)
    62686: 'APC Tents',  # CANOPY AP 16X16 WHITE (R)(G2)
    62803: 'Other Tents',  # CANOPY POLE 30 x 30 WHITE
    63851: 'Other Tents',  # TOP 6 GABLE END CAP (FOR MARQUEE
    63852: 'Other Tents',  # TOP 6X10 WHITE GABLE MID FOR FR

    # AV Equipment
    60533: 'Bullhorns',  # "BULLHORN MV10S, 16WATT (SMALL)"
    60537: 'Bullhorns',  # "BULLHORN MV16S, 20WATT (LARGE)"
    60731: 'Bubble Machines',  # "BUBBLE MACHINE, 3 DOUBLE WANDS, 11"
    60735: 'Fog Machines',  # "FOG MACHINE, HAZE, MINI"
    61543: 'Sound Systems',  # "SOUND SYSTEM, BIG FOOT v1"
    61545: 'Sound Systems',  # "SOUND SYSTEM, BIGFOOT 1.9GhZ(AA)"
    61548: 'Sound Systems',  # "SOUND SYSTEM, MiniVOX 1.9GhZ(AA)"
    61566: 'Microphones',  # "MIC, WIRELESS, HANDHELD (AA BIG FOOT V1)"
    61570: 'Microphones',  # "MIC, WIRELESS, HANDHELD 1.9GhZ(AA)"
    61571: 'Microphones',  # "MIC WIRED, HANDHELD (MINI-VOX)"
    61572: 'Microphones',  # "MIC, WIRELESS, HANDHELD  1.9GhZ(AA)"
    61573: 'Microphones',  # "MIC, WIRELESS, LAPEL 1.9GhZ(AA)"
    63343: 'Fog Machines',  # FOG MACHINE (HAZE)
    63359: 'Microphones',  # "MIC, WIRELESS, HANDHELD (SHURE)"
    63430: 'Projectors',  # "PROJECTOR, LCD, 4000 LUMENS 1080P"

    # Tables and Chairs
    63131: 'Tables',  # "TOP, TABLE ROUND, 30 INCH PLYWOOD"
    63133: 'Table Legs',  # LEG BASE 24 - 4 PRONG X
    65171: 'Table Legs',  # LEG BASE 30 - 4 PRONG X FOR 36R
    65722: 'Tables',  # "TOP, TABLE ROUND, 36 INCH PLYWOOD"
    61771: 'Chair Pads',  # CHAIRPAD CHIAVARI 2 BLACK (VEL
    61772: 'Chair Pads',  # CHAIRPAD CHIAVARI WHITE VINYL (

    # Round Linen
    61824: '90 Round',  # 90 ROUND SNOW WHITE LINEN (SEAML
    61825: '90 Round',  # 90 ROUND WHITE LINEN
    61883: '90 Round', # APPLE GREEN NOVA SOLID
    61882: '90 Round', # BERMUDA BLUE NOVA SOLID

    61826: '90 Round',  # 90 ROUND BLACK LINEN
    61827: '90 Round',  # 90 ROUND GREY LINEN
    61828: '90 Round',  # 90 ROUND IVORY LINEN
    61830: '90 Round',  # 90 ROUND KHAKI LINEN
    61831: '90 Round',  # 90 ROUND CHOCOLATE LINEN
    61832: '90 Round',  # 90 ROUND LEMON YELLOW LINEN
    61833: '90 Round',  # 90 ROUND MAIZE LINEN
    61834: '90 Round',  # 90 ROUND BYZANTINE FALL GOLD LINE
    61835: '90 Round',  # 90 ROUND POPPY LINEN
    61836: '90 Round',  # 90 ROUND PEACH LINEN
    61837: '90 Round',  # 90 ROUND ORANGE LINEN
    61838: '90 Round',  # 90 ROUND BURNT ORANGE LINEN
    61839: '90 Round',  # 90 ROUND SHRIMP LINEN
    61840: '90 Round',  # 90 ROUND RED LINEN
    61842: '90 Round',  # 90 ROUND CARDINAL RED LINEN
    61843: '90 Round',  # 90 ROUND HOT PINK LINEN
    61846: '90 Round',  # 90 ROUND PASTEL PINK LINEN
    61847: '90 Round',  # 90 ROUND PINK LINEN
    61848: '90 Round',  # 90 ROUND MAGENTA LINEN
    61850: '90 Round',  # 90 ROUND BURGUNDY LINEN
    61852: '90 Round',  # 90 ROUND GRAPE LINEN
    61854: '90 Round',  # 90 ROUND EGGPLANT LINEN
    61856: '90 Round',  # 90 ROUND AMETHYST LINEN
    61858: '90 Round',  # 90 ROUND ROYAL BLUE LINEN
    61859: '90 Round',  # 90 ROUND LIGHT BLUE LINEN
    61862: '90 Round',  # 90 ROUND TURQUOISE LINEN
    61863: '90 Round',  # 90 ROUND OCEAN BLUE LINEN
    61864: '90 Round',  # 90 ROUND PACIFICA LINEN
    61865: '90 Round',  # 90 ROUND PERIWINKLE LINEN
    61866: '90 Round',  # 90 ROUND NAVY BLUE LINEN
    61867: '90 Round',  # 90 ROUND CELADON LINEN
    61868: '90 Round',  # 90 ROUND HUNTER GREEN LINEN
    61869: '90 Round',  # 90 ROUND KELLY GREEN LINEN
    61870: '90 Round',  # 90 ROUND LIME GREEN LINEN
    61871: '90 Round',  # 90 ROUND ZEBRA PRINT LINEN
    61872: '90 Round',  # 90 ROUND PLATINUM IRIDESCENT CRUS
    61873: '90 Round',  # 90 ROUND CHAMPAGNE IRIDESCENT CRU
    61874: '90 Round',  # 90 ROUND WHITE SAND IRIDESCENT C
    61875: '90 Round',  # 90 ROUND ROSE IRIDESCENT CRUSH LI
    61876: '90 Round',  # 90 ROUND VIOLET GREEN IRIDESCENT
    61879: '90 Round',  # 90 ROUND MIMOSA NOVA SOLID LINE
    61880: '90 Round',  # 90 ROUND FUCHSIA NOVA SOLID LIN
    61881: '90 Round',  # 90 ROUND TIFFANY BLUE NOVA SOLID
    61885: '108 Round',  # 108 ROUND WHITE LINEN
    61886: '108 Round',  # 108 ROUND BLACK LINEN
    61887: '108 Round',  # 108 ROUND GREY LINEN
    61888: '108 Round',  # 108 ROUND PEWTER LINEN
    61889: '108 Round',  # 108 ROUND IVORY LINEN
    61890: '108 Round',  # 108 ROUND BEIGE LINEN
    72595: '108 Round',  #108 byz
    61891: '108 Round',  # 108 ROUND CHOCOLATE LINEN
    61893: '108 Round',  # 108 ROUND MAIZE LINEN
    61895: '108 Round',  # 108 ROUND POPPY LINEN
    61896: '108 Round',  # 108 ROUND PEACH LINEN
    61901: '108 Round',  # 108 ROUND CARDINAL RED LINEN
    61904: '108 Round',  # 108 ROUND PASTEL PINK LINEN
    61905: '108 Round',  # 108 ROUND PINK LINEN
    61908: '108 Round',  # 108 ROUND BURGUNDY LINEN
    61910: '108 Round',  # 108 ROUND GRAPE (PURPLE) LINEN
    61912: '108 Round',  # 108 ROUND EGGPLANT LINEN
    61914: '108 Round',  # 108 ROUND AMETHYST LINEN
    61916: '108 Round',  # 108 ROUND ROYAL BLUE LINEN
    61921: '108 Round',  # 108 ROUND OCEAN BLUE LINEN
    61922: '108 Round',  # 108 ROUND PACIFICA LINEN
    61924: '108 Round',  # 108 ROUND NAVY BLUE LINEN
    61925: '108 Round',  # 108 ROUND CELADON (SAGE) LINEN
    61926: '108 Round',  # 108 ROUND HUNTER GREEN LINEN
    61927: '108 Round',  # 108 ROUND KELLY GREEN LINEN
    61928: '108 Round',  # 108 ROUND LIME GREEN LINEN
    61930: '120 Round',  # 120 ROUND WHITE LINEN
    61931: '120 Round',  # 120 ROUND BLACK LINEN
    61933: '120 Round',  # 120 ROUND IVORY LINEN
    61934: '120 Round',  # 120 ROUND BEIGE LINEN
    61936: '120 Round',  # 120 ROUND CHOCOLATE LINEN
    61937: '120 Round',  # 120 ROUND LEMON YELLOW LINEN
    61939: '120 Round',  # 120 ROUND BYZANTINE FALL GOLD LIN
    61942: '120 Round',  # 120 ROUND ORANGE LINEN
    61943: '120 Round',  # 120 ROUND SHRIMP LINEN
    61946: '120 Round',  # 120 ROUND CARDINAL RED LINEN
    61949: '120 Round',  # 120 ROUND PASTEL PINK LINEN
    61950: '120 Round',  # 120 ROUND PINK LINEN
    61951: '120 Round',  # 120 ROUND MAGENTA LINEN
    61953: '120 Round',  # 120 ROUND BURGUNDY LINEN
    61955: '120 Round',  # 120 ROUND GRAPE LINEN
    61957: '120 Round',  # 120 ROUND EGGPLANT LINEN
    61958: '120 Round',  # 120 ROUND AMETHYST LINEN
    61960: '120 Round',  # 120 ROUND ROYAL BLUE LINEN
    61961: '120 Round',  # 120 ROUND LIGHT BLUE LINEN
    61962: '120 Round',  # 120 ROUND MINT LINEN
    61964: '120 Round',  # 120 ROUND TURQUOISE LINEN
    61965: '120 Round',  # 120 ROUND OCEAN BLUE LINEN
    61967: '120 Round',  # 120 ROUND PERIWINKLE LINEN
    61968: '120 Round',  # 120 ROUND NAVY BLUE LINEN
    61970: '120 Round',  # 120 ROUND HUNTER GREEN LINEN
    61971: '120 Round',  # 120 ROUND KELLY GREEN LINEN
    61972: '120 Round',  # 120 ROUND LIME GREEN LINEN
    61973: '120 Round',  # 120 ROUND DAMASK SOMERSET GOLD LI
    61974: '120 Round',  # 120 ROUND ROSE IRIDESCENT CRUSH L
    61975: '120 Round',  # 120 ROUND MIDNIGHT BLUE IRIDESCEN
    61976: '120 Round',  # 120 ROUND FUCHSIA NOVA SOLID LINE
    61977: '120 Round',  # 120 ROUND BERMUDA BLUE NOVA SOLID
    61978: '120 Round',  # 120 ROUND APPLE GREEN NOVA SOLID
    61979: '120 Round',  # 120 ROUND WHITE NOVA SWIRL LINEN
    72485: '120 Round',  # 120 ROUND DUSTY ROSE
    61981: '132 Round',  # 132 ROUND WHITE LINEN
    61982: '132 Round',  # 132 ROUND BLACK LINEN
    61984: '132 Round',  # 132 ROUND PEWTER LINEN
    61985: '132 Round',  # 132 ROUND IVORY LINEN
    61986: '132 Round',  # 132 ROUND BEIGE LINEN
    61989: '132 Round',  # 132 ROUND LEMON YELLOW LINEN
    61992: '132 Round',  # 132 ROUND POPPY LINEN
    61994: '132 Round',  # 132 ROUND ORANGE LINEN
    61996: '132 Round',  # 132 ROUND BUBBLEGUM PINK LINEN
    61999: '132 Round',  # 132 ROUND CARDINAL RED LINEN
    62003: '132 Round',  # 132 ROUND PINK LINEN
    62004: '132 Round',  # 132 ROUND MAGENTA LINEN
    62006: '132 Round',  # 132 ROUND BURGUNDY LINEN
    62010: '132 Round',  # 132 ROUND EGGPLANT LINEN
    62012: '132 Round',  # 132 ROUND AMETHYST LINEN
    62014: '132 Round',  # 132 ROUND ROYAL BLUE LINEN
    62021: '132 Round',  # 132 ROUND PERIWINKLE LINEN
    62022: '132 Round',  # 132 ROUND NAVY BLUE LINEN
    62024: '132 Round',  # 132 ROUND HUNTER GREEN LINEN
    62025: '132 Round',  # 132 ROUND KELLY GREEN LINEN
    62026: '132 Round',  # 132 ROUND LIME GREEN LINEN
    62027: '132 Round',  # 132 ROUND BURNT ORANGE LINEN
    62028: '132 Round',  # 132 ROUND ARMY GREEN LINEN
    62029: '132 Round',  # 132 ROUND DAMASK SOMERSET GOLD
    62030: '132 Round',  # 132 ROUND DAMASK CAMBRIDGE WHEAT
    62031: '132 Round',  # 132 ROUND CHAMPAGNE IRIDESCENT CR
    62032: '132 Round',  # 132 ROUND WHITE SAND IRIDESCENT
    62033: '132 Round',  # 132 ROUND SUNSET ORANGE IRD CRUSH
    62034: '132 Round',  # 132 ROUND MIDNIGHT BLUE IRIDESCEN
    62035: '132 Round',  # 132 ROUND TIFFANY BLUE NOVA SOLID

    # Rectangle Linen
    62037: 'Runners',  # LINEN RUNNER 12 X 120 WHITE
    62038: 'Runners',  # LINEN RUNNER 12 X 120 BLACK
    62039: 'Runners',  # LINEN RUNNER 12 X 120 GREY
    62040: 'Runners',  # LINEN RUNNER 12 X 120 PEWTER
    62041: 'Runners',  # LINEN RUNNER 12 X 120 IVORY
    62042: 'Runners',  # LINEN RUNNER 12 X 120 BEIGE
    62045: 'Runners',  # LINEN RUNNER 12 X 120 LEMON YEL
    62054: 'Runners',  # LINEN RUNNER 12 X 120 CARDINAL
    62057: 'Runners',  # LINEN RUNNER 12 X 120 PASTEL PI
    62065: 'Runners',  # LINEN RUNNER 12 X 120 EGGPLANT
    62067: 'Runners',  # LINEN RUNNER 12 X 120 AMETHYST
    62077: 'Runners',  # LINEN RUNNER 12 X 120 CELADON
    62081: 'Runners',  # LINEN RUNNER 12 X 120 TIFFANY B
    62082: 'Runners',  # LINEN RUNNER 13 X 120 GOLDENROD
    62083: 'Runners',  # LINEN RUNNER 13 X 120 SILVER LA
    62085: 'Caplets',  # LINEN CAPLET 30X96X10 WHITE SWIRL
    62086: 'Caplets',  # LINEN CAPLET 30X96X10 SOFT GOLD SW
    62087: 'Caplets',  # LINEN CAPLET 30X96X10 LAVENDER SWI
    62088: '60x120',  # 60X120 WHITE LINEN
    62089: '60x120',  # 60X120 BLACK LINEN
    62090: '60x120',  # 60X120 GREY LINEN
    62091: '60x120',  # 60X120 PEWTER LINEN
    62092: '60x120',  # 60X120 IVORY LINEN
    62093: '60x120',  # 60X120 BEIGE LINEN
    62094: '60x120',  # 60X120 KHAKI LINEN
    62095: '60x120',  # 60X120 CHOCOLATE LINEN
    62096: '60x120',  # 60X120 LEMON YELLOW LINEN
    62098: '60x120',  # 60X120 BYZANTINE FALL GOLD LINEN
    62099: '60x120',  # 60X120 POPPY LINEN
    62101: '60x120',  # 60X120 ORANGE LINEN
    62102: '60x120',  # 60X120 SHRIMP LINEN
    62103: '60x120',  # 60X120 BUBBLEGUM PINK LINEN
    62104: '60x120',  # 60X120 RED LINEN
    62106: '60x120',  # 60X120 CARDINAL RED LINEN
    62107: '60x120',  # 60X120 HOT PINK LINEN
    62111: '60x120',  # 60X120 PINK LINEN
    62112: '60x120',  # 60X120 MAGENTA LINEN
    62113: '60x120',  # 60X120 FLAMINGO LINEN
    62114: '60x120',  # 60X120 BURGUNDY LINEN
    62116: '60x120',  # 60X120 GRAPE LINEN
    62117: '60x120',  # 60X120 PLUM LINEN
    62118: '60x120',  # 60X120 EGGPLANT LINEN
    62119: '60x120',  # 60X120 AMETHYST LINEN
    62121: '60x120',  # 60X120 ROYAL BLUE LINEN
    62122: '60x120',  # 60X120 LIGHT BLUE LINEN
    62126: '60x120',  # 60X120 OCEAN BLUE LINEN
    62129: '60x120',  # 60X120 NAVY BLUE LINEN
    62130: '60x120',  # 60X120 CELADON LINEN
    62131: '60x120',  # 60X120 HUNTER GREEN LINEN
    62132: '60x120',  # 60X120 KELLY GREEN LINEN
    62133: '60x120',  # 60X120 LIME GREEN LINEN
    62134: '60x120',  # 60X120 BLUE GINGHAM LINEN
    62136: '60x120',  # 60X120 ROSE IRIDESCENT CRUSH LINEN
    62137: '60x120',  # 60X120 VIOLET GREEN IRIDESCENT CRU
    62138: '60x120',  # 60X120 TIFFANY BLUE NOVA SOLID LIN
    62139: '60x120',  # 60X120 SOFT SAGE NOVA SOLID LINEN
    62140: '60x120',  # 60X120 CANDY PINK NOVA SWIRL LINEN
    62141: '60x120',  # 60X120 BAMBOO NOVA SWIRL LINEN
    62142: '60x120',  # 60X120 SILVER LAME
    62187: '90x132',  # 90X132 WHITE LINEN ROUNDED CORNE
    62188: '90x132',  # 90X132 BLACK LINEN ROUNDED CORNER
    62189: '90x132',  # 90X132 GREY LINEN ROUNDED CORNERS
    62191: '90x132',  # 90X132 IVORY LINEN ROUNDED CORNER
    62194: '90x132',  # 90X132 CHOCOLATE LINEN ROUNDED CO
    62198: '90x132',  # 90X132 POPPY LINEN ROUNDED CORNER
    62204: '90x132',  # 90X132 CARDINAL RED LINEN ROUNDED
    62208: '90x132',  # 90X132 PINK LINEN ROUNDED CORNERS
    62211: '90x132',  # 90X132 BURGUNDY LINEN ROUNDED COR
    62214: '90x132',  # 90X132 PLUM LINEN ROUNDED CORNERS
    62215: '90x132',  # 90X132 EGGPLANT LINEN ROUNDED COR
    62219: '90x132',  # 90X132 ROYAL BLUE LINEN ROUNDED C
    62224: '90x132',  # 90X132 OCEAN LINEN ROUNDED CORNER
    62225: '90x132',  # 90X132 PACIFICA LINEN ROUNDED COR
    62226: '90x132',  # 90X132 PERIWINKLE LINEN ROUNDED C
    62227: '90x132',  # 90X132 NAVY BLUE LINEN ROUNDED CO
    62229: '90x132',  # 90X132 HUNTER GREEN LINEN ROUNDED
    62232: '90x132',  # 90X132 MIDNIGHT BLUE IRD CRUSH RO
    62235: '90x156',  # 90X156 WHITE LINEN ROUNDED CORNE
    62236: '90x156',  # 90X156 BLACK LINEN ROUNDED CORNER
    62237: '90x156',  # 90X156 GREY LINEN ROUNDED CORNERS
    62238: '90x156',  # 90X156 PEWTER LINEN ROUNDED CORNE
    62239: '90x156',  # 90X156 IVORY LINEN ROUNDED CORNER
    62242: '90x156',  # 90X156 CHOCOLATE LINEN ROUNDED CO
    62246: '90x156',  # 90X156 POPPY LINEN ROUNDED CORNER
    62247: '90x156',  # 90X156 PEACH LINEN ROUNDED CORNER
    62252: '90x156',  # 90X156 CARDINAL RED LINEN ROUNDED
    62255: '90x156',  # 90X156 PASTEL PINK LINEN ROUNDED
    62256: '90x156',  # 90X156 PINK LINEN ROUNDED CORNERS
    62257: '90x156',  # 90X156 MAGENTA LINEN ROUNDED CORN
    62263: '90x156',  # 90X156 EGGPLANT LINEN ROUNDED COR
    62265: '90x156',  # 90X156 AMETHYST LINEN ROUNDED COR
    62267: '90x156',  # 90X156 ROYAL BLUE LINEN ROUNDED C
    62268: '90x156',  # 90X156 LIGHT BLUE LINEN ROUNDED C
    62271: '90x156',  # 90X156 TURQUOISE LINEN ROUNDED CO
    62272: '90x156',  # 90X156 OCEAN LINEN ROUNDED CORNER
    62273: '90x156',  # 90X156 PACIFICA LINEN ROUNDED COR
    62274: '90x156',  # 90X156 PERIWINKLE LINEN ROUNDED C
    62275: '90x156',  # 90X156 NAVY BLUE LINEN ROUNDED CO
    62277: '90x156',  # 90X156 HUNTER GREEN LINEN ROUNDED
    62280: '90x156',  # 90X156 DAMASK SOMERSET GOLD LINEN
    62281: '90x156',  # 90X156 PLATINUM IRIDESCENT CRUSH L
    62282: '90x156',  # 90X156 CHAMPAGNE IRIDESCENT CRUSH
    62283: '90x156',  # 90X156 MIDNIGHT BLUE IRIDESCENT CR
    62287: '30x96 Conference',  # 30X96 CONFERENCE LINEN WHITE
    62288: '30x96 Conference',  # 30X96 CONFERENCE LINEN BLACK
    62289: '30x96 Conference',  # 30X96 CONFERENCE LINEN EGGPLANT
    62290: 'Other Rectangle Linen',  # LINEN SERPENTINE FITTED 4 WHITE
    62291: '54 Square',  # 54 SQUARE WHITE LINEN
    62292: '54 Square',  # 54 SQUARE BLACK LINEN
    62294: '54 Square',  # 54 SQUARE PEWTER LINEN
    62295: '54 Square',  # 54 SQUARE IVORY LINEN
    62298: '54 Square',  # 54 SQUARE CHOCOLATE LINEN
    62308: '54 Square',  # 54 SQUARE CARDINAL RED
    62312: '54 Square',  # 54 SQUARE PINK LINEN
    62315: '54 Square',  # 54 SQUARE BURGUNDY LINEN
    62319: '54 Square',  # 54 SQUARE EGGPLANT LINEN
    62321: '54 Square',  # 54 SQUARE AMETHYST LINEN
    62323: '54 Square',  # 54 SQUARE ROYAL BLUE LINEN
    62330: '54 Square',  # 54 SQUARE PERIWINKLE LINEN
    62331: '54 Square',  # 54 SQUARE NAVY BLUE LINEN
    62332: '54 Square',  # 54 SQUARE CELADON LINEN
    62333: '54 Square',  # 54 SQUARE HUNTER GREEN LINEN
    62336: '54 Square',  # 54 SQUARE ARMY GREEN LINEN
    62337: '54 Square',  # 54 SQUARE BURLAP (PRAIRIE) LINEN
    62338: '54 Square',  # 54 SQUARE SILVER LAME LINEN
    62339: 'Other Rectangle Linen',  # 72 SQUARE BURLAP (PRAIRIE) LINEN
    62399: '90 Square',  # 90X90 WHITE LINEN
    62401: '90 Square',  # 90X90 GREY LINEN
    62403: '90 Square',  # 90X90 IVORY LINEN
    62426: '90 Square',  # 90X90 PLUM LINEN
    62429: '90 Square',  # 90X90 AMETHYST LINEN
    65545: 'Runners',  # LINEN RUNNER 12 X 120 RED CHECK

    # Concession Equipment
    2857: 'Chocolate Fountain',  # "FOUNTAIN, CHOCOLATE"
    3290: 'Beverage Dispensers',  # "BEVERAGE COOLER, 5 GAL CAMBRO THERMOVAT"
    3727: 'Hot Dog Machines',  # HOTDOG STEAMER
    3902: 'Cheese Warmers',  # NACHO CHEESE DISPENSER and WARMER
    62468: 'Beverage Dispensers',  # "BEVERAGE COOLER, 10 GAL CAMBRO THERMOVAT"
    62475: 'Beverage Dispensers',  # "BEVERAGE DISPENSER, CLEAR-IVORY 5 GAL"
    62479: 'Beverage Dispensers',  # "BEVERAGE DISPENSER, CLEAR 5 GAL w/INFUSE"
    62535: 'Hot Dog Machines',  # "HOTDOG MACH, ROLLER (CAPACITY 50) 12AMP"
    62633: 'Chafers',  # "CHAFER, FULLSIZE, STAINLESS (GOLD TRIM)"
    62634: 'Chafers',  # "CHAFER, FULLSIZE, STAINLESS STEEL"
    62636: 'Chafers',  # "CHAFER, FULLSIZE, ROLLTOP, STAINLESS 8QT"
    62637: 'Chafers',  # "CHAFER, HALFSIZE, STAINLESS STEEL"
    62651: 'Fountains',  # "FOUNTAIN, 3 GAL PRINCESS (6AMP)"
    62652: 'Fountains',  # "FOUNTAIN, 7 GAL PRINCESS (6 AMP)"
    62653: 'Fountains',  # "FOUNTAIN, 4 1/2 GAL EMPRESS (6 AMP)"
    62654: 'Fountains',  # "FOUNTAIN, 3 GAL EMPRESS (6 AMP)"
    63791: 'Cheese Warmers',  # "WARMER 3-1/2 QT, ELECTRIC (5amp, 120v)"
    63793: 'Cheese Warmers',  # "WARMER 3-1/2 QT, ELECTRIC (HEATED STEM)"
    63806: 'Frozen Drink Machines',  # FROZEN DRINK MACHINE -SINGLE BARREL
    66715: 'Donut Machines',  # MINI DONUT MACHINE
    68317: 'Frozen Drink Machines',  # FROZEN DRINK MACHINE - OTC (6 AMP)
    68318: 'Popcorn Machines',  # "POPCORN MACHINE, 8 oz DELV CASE"
    68320: 'Popcorn Machines',  # "POPCORN MACHINE, 8 OZ,10AMP, TABLETOP"
    68321: 'Sno Cone Machines',  # "SNO-KONE MACHINE, 7 AMP ELECTRIC"
    68322: 'Cotton Candy Machines',  # "COTTON CANDY MACHINE, 9 AMP 120V"
    68332: 'Frozen Drink Machines',  # FROZEN DRINK MACHINE -DOUBLE BARREL

    # Runners and Drapes
    63278: '16 ft',  # "DRAPES, BLACK 16 X 48 (ADJ 10,12,16)"
    63295: '3 ft',  # "DRAPES, BLACK 3 X 48 BANJO"
    63296: '3 ft',  # "DRAPES, SILVER 3 X 48 BANJO"
    63297: '3 ft',  # "DRAPES, BLUE 3 X 48 BANJO"
    63298: '8 ft',  # "DRAPES, WHITE -ARCTIC SNOW, 8X 4"
    63299: '8 ft',  # "DRAPES, BLACK 8 X 58 VELOUR"
    63300: '8 ft',  # "DRAPES, BLACK 8 X 48 BANJO"
    63301: '8 ft',  # "DRAPES, SILVER 8 X 48 BANJO"
    63302: '8 ft',  # "DRAPES, CHARCOAL, 8 X 48 BANJO"
    63303: '8 ft',  # "DRAPES, IVORY, 8 X 48 BANJO"
    63304: '8 ft',  # "DRAPES, GOLD, 8 X 48 BANJO"
    63305: '8 ft',  # "DRAPES, ORANGE, 8 X 48 BANJO"
    63306: '8 ft',  # "DRAPES, RED, 8 X 48 BANJO"
    63307: '8 ft',  # "DRAPES, BURGUNDY 8 X 48 BANJO"
    63308: '8 ft',  # "DRAPES, RASPBERRY, 8 X 48 BANJO"
    63309: '8 ft',  # "DRAPES, PURPLE, 8 X 48 BANJO"
    63310: '8 ft',  # "DRAPES, BLUE 8 X 48 BANJO"
    63311: '8 ft',  # "DRAPES, WHITE -SHEER 8H X 118W"
    63313: '8 ft',  # "DRAPES, NAVY BLUE, 8 X 48 BANJO"
    63314: '8 ft',  # "DRAPES, FOREST GREEN 8 X 48 BANJO"
    63315: '8 ft',  # "DRAPES, HUNTER GREEN 8 X 48 BANJO"
    63316: '16 ft',  # "DRAPES, BLACK 16 X 48 BANJO"
    63317: '16 ft',  # "DRAPES, WHITE -SHEER 16H X 118W"
    63327: 'Red Runner',  # "CARPET RUNNER, RED 4 X 25 (G1)"
    63328: 'Red Runner',  # "CARPET RUNNER, RED 4 X 25 (G2)"
    63329: 'Red Runner',  # "CARPET RUNNER, RED 4 X 50 (G1)"
    63330: 'Red Runner',  # "CARPET RUNNER, RED 4 X 50 (G2)"
    63331: 'Purple Runner',  # "CARPET RUNNER, PURPLE 4 X 25"
    63332: 'Purple Runner',  # "CARPET RUNNER, PURPLE 4 X 50 (G1)"
    64836: 'Resale Runners',  # AISLE CLOTH 75 WHITE
    64837: 'Resale Runners',  # AISLE CLOTH 100 WHITE
    66688: '8 ft',  # "DRAPES, BLACK 8 X 48 POLY"

    # Other
    61749: 'Linens',  # BAG FOR SOILED LINEN
    61750: 'Stage Skirts',  # SKIRT STAGE 24 X 13 BLACK BAN
    61758: 'Stage Skirts',  # SKIRT STAGE 44 X 13 BLACK BAN
    61759: 'Stage Skirts',  # SKIRT 8 WHITE (30)
    61760: 'Stage Skirts',  # SKIRT 8 BLACK (30)
    61761: 'Stage Skirts',  # SKIRT 14 WHITE (30)
    61762: 'Stage Skirts',  # SKIRT 14 BLACK (30)
    61763: 'Stage Skirts',  # SKIRT 14 IVORY (30)
    61764: 'Stage Skirts',  # SKIRT 21 WHITE (30)
    62445: 'Spandex Linens',  # SPANDEX LINEN WHITE 30 X 42 (W/BLK F
    62447: 'Spandex Linens',  # SPANDEX LINEN BLACK 30x42 (COCKTAIL)
    62449: 'Spandex Linens',  # SPANDEX ICE TABLE SKIRT BLACK (SMALL)
    62451: 'Spandex Linens',  # SPANDEX ICE TABLE SKIRT WHITE (LARGE)
    62452: 'Spandex Linens',  # SPANDEX ICE TABLE SKIRT BLACK (LARGE)
    62233: 'Spandex Linens',  # SPANDEX TABLE LINEN WHITE 6X30 BANQ
    62234: 'Spandex Linens',  # SPANDEX TABLE LINEN BLACK 6X30 BANQ
    62284: 'Spandex Linens',  # SPANDEX TABLE LINEN WHITE 8X30 BANQ
    62285: 'Spandex Linens',  # SPANDEX TABLE LINEN BLACK 8X30 BANQ
    67139: 'Spandex Linens',  # SPANDEX LINEN WHITE 36 X 42
    67140: 'Spandex Linens',  # SPANDEX LINEN BLACK 36 X 42
    99999: 'Miscellaneous',  # HP 15x15 IKEs Bar

    # Resale
    1: 'Test',  # test resale
    3168: 'Chocolate',  # CHOCOLATE BAG 2LB. DARK
    3169: 'Chocolate',  # CHOCOLATE BAG 2LB. MILK
    3903: 'Cheese',  # NACHO CHEESE 140oz BAG
    64815: 'Fog and Bubbles',  # FOG SOLUTION (GROUND) 1 QUART
    64816: 'Fog and Bubbles',  # FOG SOLUTION (HAZE) 1 QUART
    64817: 'Fog and Bubbles',  # BUBBLE JUICE 1 QUART
    64819: 'Fuel',  # FUEL STERNO 8 OZ -LASTS 2+HRS
    64824: 'Fuel',  # FUEL BUTANE CARTRIDGE 8 OUNCE
    64840: 'Cotton Candy Supplies',  # COTTON CANDY SUGAR PINK VANILLA (52 OZ
    64841: 'Cotton Candy Supplies',  # COTTON CANDY SUGAR BLUE RASPBERRY-52oz
    64842: 'Cotton Candy Supplies',  # COTTON CANDY SUGAR CHERRY (52 OZ CARTON
    64843: 'Cotton Candy Supplies',  # COTTON CANDY SUGAR STRAWBERRY (52 OZ CA
    64847: 'Cotton Candy Supplies',  # COTTON CANDY BAGS & TIES 100 PER PKG
    64848: 'Cotton Candy Supplies',  # COTTON CANDY CONES 100 PER PKG.
    64849: 'Cotton Candy Supplies',  # COTTON CANDY SUGAR BUBBLE GUM (52 OZ CA
    64852: 'Popcorn Supplies',  # POPCORN/SALT/OIL PRE-MEASURED KIT
    64853: 'Popcorn Supplies',  # POPCORN BAGS 50/ PKG
    64854: 'Cheese',  # NACHO CHEESE SAUCE #10 CAN
    64855: 'Sno Cone Supplies',  # SNOKONE SYRUP **LIME** 1 GALLON
    64856: 'Sno Cone Supplies',  # SNOKONE SYRUP **GRAPE** 1 GALLON
    64857: 'Sno Cone Supplies',  # SNOKONE SYRUP **CHERRY** 1 GALLON
    64858: 'Sno Cone Supplies',  # SNOKONE SYRUP **BLUE RASPBERRY 1 GALLON
    64860: 'Sno Cone Supplies',  # SNOKONE KONES 200 COUNT BOX
    64861: 'Sno Cone Supplies',  # SNOKONE SYRUP PUMP (1 GAL)
    64864: 'Frozen Drink Frusheeze',  # FRUSHEEZE STRAWBERRY DAQ 1/2 GALLON
    64865: 'Frozen Drink Frusheeze',  # FRUSHEEZE FRUIT PUNCH 1/2 GALLON
    64866: 'Frozen Drink Frusheeze',  # FRUSHEEZE MARGARITA 1/2 GALLON
    64867: 'Frozen Drink Frusheeze',  # FRUSHEEZE BLUE RASPBERRY 1/2 GALLON
    64868: 'Frozen Drink Frusheeze',  # FRUSHEEZE PINA COLADA 1/2 GALLON
    64869: 'Frozen Drink Frusheeze',  # FRUSHEEZE CHERRY 1/2 GALLON
    64874: 'Frozen Drink Frusheeze',  # FRUSHEEZE LEMONADE GRANITA MIX 1 GAL (5
    64876: 'Other Resale',  # GARBAGE CAN DISPOSABLE 35 GAL W/ LID
    64888: 'Kwik Covers 30 & 36 Round',  # KWIK COVER WHITE ROUND 30 PLASTIC
    64889: 'Kwik Covers 30 & 36 Round',  # KWIK COVER BLACK ROUND 30 PLASTIC
    64890: 'Kwik Covers 30 & 36 Round',  # KWIK COVER RED ROUND 30 PLASTIC
    64891: 'Kwik Covers 30 & 36 Round',  # KWIK COVER GINGHAM RED ROUND 30 PLASTI
    64892: 'Kwik Covers 30 & 36 Round',  # KWIK COVER ROYAL BLUE ROUND 30
    64893: 'Kwik Covers 30 & 36 Round',  # KWIK COVER HUNTER GREEN ROUND 30 PLAST
    65604: 'Kwik Covers 30 & 36 Round',  # KWIK COVER BLACK ROUND 36
    65605: 'Kwik Covers 30 & 36 Round',  # KWIK COVER WHITE ROUND 36
    65606: 'Kwik Covers 30 & 36 Round',  # KWIK COVER HUNTER GREEN ROUND 36
    65607: 'Kwik Covers 30 & 36 Round',  # KWIK COVER ROYAL BLUE ROUND 36
    65608: 'Kwik Covers 30 & 36 Round',  # KWIK COVER RED ROUND 36
    65609: 'Kwik Covers 30 & 36 Round',  # KWIK COVER GINGHAM RED ROUND 36
    64894: 'Kwik Covers 4 ft Round',  # KWIK COVER WHITE ROUND 48 PLASTIC
    64895: 'Kwik Covers 4 ft Round',  # KWIK COVER BLACK ROUND 48 PLASTIC
    64896: 'Kwik Covers 4 ft Round',  # KWIK COVER SUNSHINE GOLD ROUND 48 PLAS
    64897: 'Kwik Covers 4 ft Round',  # KWIK COVER ORANGE ROUND 48 PLASTIC
    64898: 'Kwik Covers 4 ft Round',  # KWIK COVER RED ROUND 48 PLASTIC
    64899: 'Kwik Covers 4 ft Round',  # KWIK COVER GINGHAM RED ROUND 48 PLASTI
    64900: 'Kwik Covers 4 ft Round',  # KWIK COVER MAROON ROUND 48 PLASTIC
    64901: 'Kwik Covers 4 ft Round',  # KWIK COVER PURPLE ROUND 48 PLASTIC
    64902: 'Kwik Covers 4 ft Round',  # KWIK COVER ROYAL BLUE ROUND 48 PLASTIC
    64904: 'Kwik Covers 4 ft Round',  # KWIK COVER HUNTER GREEN ROUND 48 PLAST
    64905: 'Kwik Covers 4 ft Round',  # KWIK COVER BLACK & WHITE CHECK ROUND 48
    63440: 'Kwik Covers 4 ft Round',  # KWIK COVER GINGHAM BLUE ROUND 48
    64906: 'Kwik Covers 5 ft Round',  # KWIK COVER WHITE ROUND 60 PLASTIC
    64907: 'Kwik Covers 5 ft Round',  # KWIK COVER BLACK ROUND 60 PLASTIC
    64908: 'Kwik Covers 5 ft Round',  # KWIK COVER SUNSHINE GOLD ROUND 60 PLAS
    64909: 'Kwik Covers 5 ft Round',  # KWIK COVER ORANGE ROUND 60 PLASTIC
    64910: 'Kwik Covers 5 ft Round',  # KWIK COVER RED ROUND 60 PLASTIC
    64911: 'Kwik Covers 5 ft Round',  # KWIK COVER GINGHAM RED ROUND 60 PLASTI
    64912: 'Kwik Covers 5 ft Round',  # KWIK COVER PINK ROUND 60 PLASTIC
    64913: 'Kwik Covers 5 ft Round',  # KWIK COVER MAROON ROUND 60 PLASTIC
    64914: 'Kwik Covers 5 ft Round',  # KWIK COVER PURPLE ROUND 60 PLASTIC
    64915: 'Kwik Covers 5 ft Round',  # KWIK COVER ROYAL BLUE ROUND 60 PLASTIC
    64916: 'Kwik Covers 5 ft Round',  # KWIK COVER LIGHT BLUE ROUND 60 PLASTIC
    64917: 'Kwik Covers 5 ft Round',  # KWIK COVER GINGHAM BLUE ROUND 60 PLAST
    64918: 'Kwik Covers 5 ft Round',  # KWIK COVER HUNTER GREEN ROUND 60 PLAST
    64919: 'Kwik Covers 5 ft Round',  # KWIK COVER LIME GREEN ROUND 60 PLASTIC
    64920: 'Kwik Covers 5 ft Round',  # KWIK COVER BLACK & WHITE CHECK ROUND 60
    65495: 'Kwik Covers 5 ft Round',  # KWIK COVER SILVER 60 ROUND
    65498: 'Kwik Covers 5 ft Round',  # KWIK COVER NAVY BLUE 60 ROUND
    64921: 'Kwik Covers 6 ft Banquet',  # KWIK COVER WHITE 6 X 30 PLASTIC
    64922: 'Kwik Covers 6 ft Banquet',  # KWIK COVER BLACK 6 X 30 PLASTIC
    64923: 'Kwik Covers 6 ft Banquet',  # KWIK COVER SUNSHINE GOLD 6 X 30 PLAST
    64924: 'Kwik Covers 6 ft Banquet',  # KWIK COVER ORANGE 6 X 30 PLASTIC
    64925: 'Kwik Covers 6 ft Banquet',  # KWIK COVER RED 6 X 30 PLASTIC
    64926: 'Kwik Covers 6 ft Banquet',  # KWIK COVER GINGHAM RED 6 X 30 PLASTIC
    64927: 'Kwik Covers 6 ft Banquet',  # KWIK COVER PINK 6 X 30 PLASTIC
    64928: 'Kwik Covers 6 ft Banquet',  # KWIK COVER MAROON 6 X 30 PLASTIC
    64929: 'Kwik Covers 6 ft Banquet',  # KWIK COVER PURPLE 6 X 30 PLASTIC
    64930: 'Kwik Covers 6 ft Banquet',  # KWIK COVER ROYAL BLUE 6 X 30 PLASTIC
    64932: 'Kwik Covers 6 ft Banquet',  # KWIK COVER HUNTER GREEN 6 X 30 PLASTI
    64933: 'Kwik Covers 6 ft Banquet',  # KWIK COVER LIME GREEN 6 X 30 PLASTIC
    64934: 'Kwik Covers 6 ft Banquet',  # KWIK COVER BLACK & WHITE CHECK 6 X 30
    65493: 'Kwik Covers 6 ft Banquet',  # KWIK COVER SILVER 6 x 30 BANQ
    65496: 'Kwik Covers 6 ft Banquet',  # KWIK COVER NAVY BLUE 6 x 30 BANQ
    63442: 'Kwik Covers 6 ft Banquet',  # KWIK COVER GINGHAM BLUE 6 X 30
    64935: 'Kwik Covers 8 ft Banquet',  # KWIK COVER WHITE 8 X 30 PLASTIC
    64936: 'Kwik Covers 8 ft Banquet',  # KWIK COVER BLACK 8 X 30 PLASTIC
    64937: 'Kwik Covers 8 ft Banquet',  # KWIK COVER SUNSHINE GOLD 8 X 30 PLAST
    64938: 'Kwik Covers 8 ft Banquet',  # KWIK COVER ORANGE 8 X 30 PLASTIC
    64939: 'Kwik Covers 8 ft Banquet',  # KWIK COVER RED 8 X 30 PLASTIC
    64940: 'Kwik Covers 8 ft Banquet',  # KWIK COVER GINGHAM RED 8 X 30 PLASTIC
    64941: 'Kwik Covers 8 ft Banquet',  # KWIK COVER PINK 8 X 30 PLASTIC
    64942: 'Kwik Covers 8 ft Banquet',  # KWIK COVER MAROON 8 X 30 PLASTIC
    64943: 'Kwik Covers 8 ft Banquet',  # KWIK COVER PURPLE 8 X 30 PLASTIC
    64944: 'Kwik Covers 8 ft Banquet',  # KWIK COVER ROYAL BLUE 8 X 30 PLASTIC
    64945: 'Kwik Covers 8 ft Banquet',  # KWIK COVER LIGHT BLUE 8 X 30 PLASTIC
    64946: 'Kwik Covers 8 ft Banquet',  # KWIK COVER GINGHAM BLUE 8 X 30
    64947: 'Kwik Covers 8 ft Banquet',  # KWIK COVER HUNTER GREEN 8 X 30 PLASTI
    64948: 'Kwik Covers 8 ft Banquet',  # KWIK COVER LIME GREEN 8 X 30 PLASTIC
    64949: 'Kwik Covers 8 ft Banquet',  # KWIK COVER BLACK & WHITE CHECK 8 X 30
    65494: 'Kwik Covers 8 ft Banquet',  # KWIK COVER SILVER 8 x 30 BANQ
    65497: 'Kwik Covers 8 ft Banquet',  # KWIK COVER NAVY BLUE 8 x 30 BANQ
    65611: 'Kwik Covers 4 ft Banquet White',  # KWIK COVER WHITE 4 x 30 BANQ

    # Resale (continued)
    66742: 'Donut Supplies',  # DONUT BAGS-MINI 70ct
    66743: 'Donut Supplies',  # DONUT SUGAR 5 LBS & DISPENSER
    66747: 'Donut Supplies',  # MINI DONUT -70 SERVINGS- SUPPLY PACKAGE
    65808: 'Sno Cone Supplies',  # SNOKONE SYRUP **PINK LEMONADE** 1 GALLON
}

def categorize_item(rental_class_id):
    return CATEGORY_MAP.get(int(rental_class_id or 0), 'Other')

def subcategorize_item(category, rental_class_id):
    rid = int(rental_class_id or 0)
    if category in ['Tent Tops', 'Tables and Chairs', 'Round Linen', 'Rectangle Linen', 
                    'Concession Equipment', 'AV Equipment', 'Runners and Drapes', 
                    'Other', 'Resale']:
        return SUBCATEGORY_MAP.get(rid, 'Unspecified Subcategory')
    return 'Unspecified Subcategory'

@tab2_bp.route("/")
def show_tab2():
    print("Loading /tab2/ endpoint")
    with DatabaseConnection() as conn:
        items = conn.execute("SELECT * FROM id_item_master").fetchall()
        contracts = conn.execute("SELECT DISTINCT last_contract_num, client_name, MAX(date_last_scanned) as scan_date FROM id_item_master WHERE last_contract_num IS NOT NULL GROUP BY last_contract_num").fetchall()
    items = [dict(row) for row in items]
    contract_map = {c["last_contract_num"]: {"client_name": c["client_name"], "scan_date": c["scan_date"]} for c in contracts}

    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_map = defaultdict(list)
    for item in filtered_items:
        cat = categorize_item(item.get("rental_class_num"))
        category_map[cat].append(item)

    parent_data = []
    sub_map = {}
    for category, item_list in category_map.items():
        available = sum(1 for item in item_list if item["status"] == "Ready to Rent")
        on_rent = sum(1 for item in item_list if item["status"] in ["On Rent", "Delivered"])
        service = len(item_list) - available - on_rent
        client_name = contract_map.get(item_list[0]["last_contract_num"], {}).get("client_name", "N/A") if item_list and item_list[0]["last_contract_num"] else "N/A"
        scan_date = contract_map.get(item_list[0]["last_contract_num"], {}).get("scan_date", "N/A") if item_list and item_list[0]["last_contract_num"] else "N/A"

        temp_sub_map = defaultdict(lambda: defaultdict(list))
        for itm in item_list:
            subcat = subcategorize_item(category, itm.get("rental_class_num"))
            common_name = itm.get("common_name", "Unknown")
            temp_sub_map[subcat][common_name].append(itm)

        sub_map[category] = {
            "subcategories": {
                subcat: {
                    "common_names": {cn: {"total": len(items)} for cn, items in subcat_items.items()}
                } for subcat, subcat_items in temp_sub_map.items()
            }
        }

        parent_data.append({
            "category": category,
            "total": len(item_list),
            "available": available,
            "on_rent": on_rent,
            "service": service,
            "client_name": client_name,
            "scan_date": scan_date
        })

    parent_data.sort(key=lambda x: x["category"])
    expand_category = request.args.get('expand', None)

    return render_template(
        "tab2.html",
        parent_data=parent_data,
        sub_map=sub_map,
        expand_category=expand_category,
        filter_common_name=filter_common_name,
        filter_tag_id=filter_tag_id,
        filter_bin_location=filter_bin_location,
        filter_last_contract=filter_last_contract,
        filter_status=filter_status
    )

@tab2_bp.route("/subcat_data", methods=["GET"])
def subcat_data():
    print("Hit /tab2/subcat_data endpoint")
    category = request.args.get('category')
    subcat = request.args.get('subcat')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows]

    filter_common_name = request.args.get("common_name", "").lower().strip()
    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_common_name:
        filtered_items = [item for item in filtered_items if filter_common_name in (item.get("common_name") or "").lower()]
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_items = [item for item in filtered_items if categorize_item(item.get("rental_class_num")) == category]
    subcat_items = [item for item in category_items if subcategorize_item(category, item.get("rental_class_num")) == subcat]

    common_name_map = defaultdict(list)
    for item in subcat_items:
        common_name_map[item.get("common_name", "Unknown")].append(item)

    total_common_names = len(common_name_map)
    total_pages = (total_common_names + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_common_names = list(common_name_map.keys())[start:end]

    print(f"AJAX: Category: {category}, Subcategory: {subcat}, Total Common Names: {total_common_names}, Page: {page}")

    return jsonify({
        "common_names": [{
            "common_name": cn,
            "total": len(common_name_map[cn])
        } for cn in paginated_common_names],
        "total_common_names": total_common_names,
        "total_pages": total_pages,
        "current_page": page
    })

@tab2_bp.route("/item_data", methods=["GET"])
def item_data():
    print("Hit /tab2/item_data endpoint")
    category = request.args.get('category')
    subcat = request.args.get('subcat')
    common_name = request.args.get('common_name')
    page = int(request.args.get('page', 1))
    per_page = 20

    with DatabaseConnection() as conn:
        rows = conn.execute("SELECT * FROM id_item_master").fetchall()
    items = [dict(row) for row in rows]

    filter_tag_id = request.args.get("tag_id", "").lower().strip()
    filter_bin_location = request.args.get("bin_location", "").lower().strip()
    filter_last_contract = request.args.get("last_contract_num", "").lower().strip()
    filter_status = request.args.get("status", "").lower().strip()

    filtered_items = items
    if filter_tag_id:
        filtered_items = [item for item in filtered_items if filter_tag_id in (item.get("tag_id") or "").lower()]
    if filter_bin_location:
        filtered_items = [item for item in filtered_items if filter_bin_location in (item.get("bin_location") or "").lower()]
    if filter_last_contract:
        filtered_items = [item for item in filtered_items if filter_last_contract in (item.get("last_contract_num") or "").lower()]
    if filter_status:
        filtered_items = [item for item in filtered_items if filter_status in (item.get("status") or "").lower()]

    category_items = [item for item in filtered_items if categorize_item(item.get("rental_class_num")) == category]
    subcat_items = [item for item in category_items if subcategorize_item(category, item.get("rental_class_num")) == subcat]
    common_items = [item for item in subcat_items if item.get("common_name", "Unknown") == common_name]

    total_items = len(common_items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = common_items[start:end]

    print(f"AJAX: Category: {category}, Subcategory: {subcat}, Common Name: {common_name}, Total Items: {total_items}, Page: {page}")

    return jsonify({
        "items": [{
            "tag_id": item["tag_id"],
            "common_name": item["common_name"],
            "status": item["status"],
            "bin_location": item.get("bin_location", "N/A"),
            "quality": item.get("quality", "N/A"),
            "last_contract_num": item.get("last_contract_num", "N/A"),
            "date_last_scanned": item.get("date_last_scanned", "N/A"),
            "last_scanned_by": item.get("last_scanned_by", "N/A"),
            "notes": item.get("notes", "N/A")
        } for item in paginated_items],
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    })

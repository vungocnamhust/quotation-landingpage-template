#!/usr/bin/env python3
"""
Generate a luxury-styled editable Word Document (.docx) for quotation quo_ac7d18dd7459
matching the visual design, color palette, and layout of pdf.html.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
import html


def xml_escape(text: str | None) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def emu(inches: float) -> int:
    return int(inches * 914400)


def create_drawing_xml(rId: str, width_in: float, height_in: float, desc: str = "Image") -> str:
    cx = emu(width_in)
    cy = emu(height_in)
    return f"""<w:r>
      <w:drawing>
        <wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
          <wp:extent cx="{cx}" cy="{cy}"/>
          <wp:effectExtent l="0" t="0" r="0" b="0"/>
          <wp:docPr id="1" name="{xml_escape(desc)}"/>
          <wp:cNvGraphicFramePr>
            <a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>
          </wp:cNvGraphicFramePr>
          <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:nvPicPr>
                  <pic:cNvPr id="0" name="{xml_escape(desc)}"/>
                  <pic:cNvPicPr/>
                </pic:nvPicPr>
                <pic:blipFill>
                  <a:blip r:embed="{rId}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
                  <a:stretch>
                    <a:fillRect/>
                  </a:stretch>
                </pic:blipFill>
                <pic:spPr>
                  <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="{cx}" cy="{cy}"/>
                  </a:xfrm>
                  <a:prstGeom prst="rect">
                    <a:avLst/>
                  </a:prstGeom>
                </pic:spPr>
              </pic:pic>
            </a:graphicData>
          </a:graphic>
        </wp:inline>
      </w:drawing>
    </w:r>"""


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    quotation_id = "quo_ac7d18dd7459"
    ctx_path = os.path.join(repo_root, "published", quotation_id, "ctx.json")
    public_dir = os.path.join(repo_root, "quote-generator", "public")

    if not os.path.exists(ctx_path):
        print(f"Error: ctx.json not found at {ctx_path}", file=sys.stderr)
        sys.exit(1)

    with open(ctx_path, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    # Image registration map
    images_to_embed = {}
    rel_id_counter = 2
    image_rels = []

    def register_image(rel_path: str) -> str | None:
        nonlocal rel_id_counter
        if not rel_path:
            return None
        full_path = public_dir + rel_path if rel_path.startswith("/") else os.path.join(repo_root, rel_path)
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            return None
        if rel_path in images_to_embed:
            return images_to_embed[rel_path]["rId"]

        r_id = f"rIdImg{rel_id_counter}"
        ext = os.path.splitext(full_path)[1].lower()
        if ext == ".svg":
            # Word handles PNG/JPG best
            return None
        media_name = f"image{rel_id_counter}{ext}"
        rel_id_counter += 1

        with open(full_path, "rb") as fp:
            img_bytes = fp.read()

        images_to_embed[rel_path] = {
            "rId": r_id,
            "media_name": media_name,
            "bytes": img_bytes,
            "full_path": full_path,
        }
        image_rels.append((r_id, f"media/{media_name}"))
        return r_id

    # Register assets
    logo_rid = register_image("/assets/brands/capella_travel.png")
    hero_rid = register_image("/assets/ha-noi/hanoi1.jpg")
    designer_rid = register_image("/assets/dias_team/hieu.jpg")
    fansipan_rid = register_image("/assets/lao-cai/fansipan.jpg")
    tamcoc_rid = register_image("/assets/ninh-binh/tamcoc.jpg")
    halong_rid = register_image("/assets/quang-ninh/halong-bay.jpg")
    train_rid = register_image("/assets/hotels/lao-cai/chapa-express-train/exterior/exterior_2.jpg")
    jade_rid = register_image("/assets/hotels/lao-cai/sapa-jade-hill/exterior/exterior_1.jpg")
    jardin_rid = register_image("/assets/hotels/hanoi/hanoi-le-jardin-hotel-spa/exterior/exterior_3.jpg")
    cruise_rid = register_image("/assets/hotels/halong/ambassador-signature-cruise/exterior/exterior_4.jpg")

    body_xml_parts = []

    # 1. LUXURY COVER / HEADER BANNER
    logo_drawing = create_drawing_xml(logo_rid, 1.8, 0.6, "Capella Travel Logo") if logo_rid else ""
    hero_drawing = create_drawing_xml(hero_rid, 6.5, 2.4, "Vietnam Landscape") if hero_rid else ""

    body_xml_parts.append(f"""
    <!-- COVER / HERO BANNER -->
    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="9740" w:type="dxa"/>
        <w:tblBorders>
          <w:top w:val="none"/>
          <w:left w:val="none"/>
          <w:bottom w:val="single" w:sz="24" w:space="0" w:color="CBA135"/>
          <w:right w:val="none"/>
        </w:tblBorders>
        <w:tblCellMar>
          <w:top w:w="240" w:type="dxa"/>
          <w:bottom w:w="240" w:type="dxa"/>
          <w:left w:w="280" w:type="dxa"/>
          <w:right w:w="280" w:type="dxa"/>
        </w:tblCellMar>
      </w:tblPr>
      <w:tr>
        <w:tc>
          <w:tcPr>
            <w:tcW w:w="9740" w:type="dxa"/>
            <w:shd w:val="clear" w:color="auto" w:fill="17412E"/>
          </w:tcPr>
          <w:p>
            <w:pPr><w:jc w:val="right"/></w:pPr>
            {logo_drawing}
          </w:p>
          <w:p>
            <w:pPr>
              <w:spacing w:before="120" w:after="60"/>
            </w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                <w:color w:val="CBA135"/>
                <w:b/>
                <w:sz w:val="26"/>
              </w:rPr>
              <w:t>CAPELLA TRAVEL · PRIVATE LUXURY QUOTATION</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr>
              <w:spacing w:before="60" w:after="120"/>
            </w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                <w:color w:val="FFFFFF"/>
                <w:b/>
                <w:sz w:val="56"/>
              </w:rPr>
              <w:t>{xml_escape(ctx.get('tour_title') or "Anisha's Family Trip")}</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr>
              <w:spacing w:before="0" w:after="180"/>
            </w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="D8BD85"/>
                <w:i/>
                <w:sz w:val="28"/>
              </w:rPr>
              <w:t>{xml_escape(ctx.get('quotation_title') or "Bespoke Northern Vietnam Exploration")}</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr>
              <w:spacing w:before="0" w:after="120"/>
            </w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="FFFFFF"/>
                <w:sz w:val="22"/>
              </w:rPr>
              <w:t>8 Days 7 Nights  |  30 Sep – 07 Oct 2026  |  5 Adults  |  Ref: {xml_escape(ctx.get('quotation_number') or 'QT-2026-CAPELLA-8D7N-IND')}</w:t>
            </w:r>
          </w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr>{hero_drawing}</w:p>
    """)

    # 2. PERSONAL NOTE & DESIGNER LETTER
    body_xml_parts.append(f"""
    <!-- PERSONAL LETTER SECTION -->
    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="9740" w:type="dxa"/>
        <w:tblBorders>
          <w:top w:val="none"/>
          <w:left w:val="single" w:sz="36" w:space="0" w:color="CBA135"/>
          <w:bottom w:val="none"/>
          <w:right w:val="none"/>
        </w:tblBorders>
        <w:tblCellMar>
          <w:top w:w="200" w:type="dxa"/>
          <w:bottom w:w="200" w:type="dxa"/>
          <w:left w:w="260" w:type="dxa"/>
          <w:right w:w="260" w:type="dxa"/>
        </w:tblCellMar>
      </w:tblPr>
      <w:tr>
        <w:tc>
          <w:tcPr>
            <w:tcW w:w="9740" w:type="dxa"/>
            <w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/>
          </w:tcPr>
          <w:p>
            <w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                <w:color w:val="17412E"/>
                <w:b/>
                <w:sz w:val="34"/>
              </w:rPr>
              <w:t>A Personal Note for Your Journey</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr><w:spacing w:before="60" w:after="120"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="11130F"/>
                <w:b/>
                <w:sz w:val="24"/>
              </w:rPr>
              <w:t>Dear {xml_escape(ctx.get('customer_name') or 'Anisha')},</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr><w:spacing w:before="0" w:after="120"/><w:jc w:val="both"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="333333"/>
                <w:sz w:val="22"/>
              </w:rPr>
              <w:t>{xml_escape(ctx.get('lede') or '')}</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr><w:spacing w:before="60" w:after="120"/><w:jc w:val="both"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="333333"/>
                <w:sz w:val="22"/>
              </w:rPr>
              <w:t>We have poured our expertise and passion into crafting every detail of this journey, and we cannot wait for you to experience the magic of Vietnam. Please review the itinerary below, and let us know if you would like any refinements.</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                <w:color w:val="CBA135"/>
                <w:i/>
                <w:b/>
                <w:sz w:val="28"/>
              </w:rPr>
              <w:t>Warm regards,</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="17412E"/>
                <w:b/>
                <w:sz w:val="24"/>
              </w:rPr>
              <w:t>Eddie (Pham Trung Hieu) — Lead Travel Designer</w:t>
            </w:r>
          </w:p>
          <w:p>
            <w:pPr><w:spacing w:before="0" w:after="60"/></w:pPr>
            <w:r>
              <w:rPr>
                <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                <w:color w:val="706A5D"/>
                <w:sz w:val="20"/>
              </w:rPr>
              <w:t>Capella Travel  |  Phone: +84 911 538 738  |  Email: sales@capellatravel.com</w:t>
            </w:r>
          </w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:pPr><w:spacing w:before="180" w:after="120"/></w:pPr></w:p>
    """)

    # 3. TRIP AT A GLANCE TABLE
    body_xml_parts.append(f"""
    <!-- SECTION HEADING: TRIP AT A GLANCE -->
    <w:p>
      <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>Trip at a Glance</w:t>
      </w:r>
    </w:p>

    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="9740" w:type="dxa"/>
        <w:tblBorders>
          <w:top w:val="single" w:sz="6" w:color="D8BD85"/>
          <w:left w:val="none"/>
          <w:bottom w:val="single" w:sz="6" w:color="D8BD85"/>
          <w:right w:val="none"/>
          <w:insideH w:val="single" w:sz="4" w:color="E5D5BA"/>
          <w:insideV w:val="none"/>
        </w:tblBorders>
        <w:tblCellMar>
          <w:top w:w="120" w:type="dxa"/>
          <w:bottom w:w="120" w:type="dxa"/>
          <w:left w:w="180" w:type="dxa"/>
          <w:right w:w="180" w:type="dxa"/>
        </w:tblCellMar>
      </w:tblPr>
      
      <!-- Row 1: Duration & Dates -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Duration &amp; Dates</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
          <w:p><w:r><w:rPr><w:color w:val="11130F"/><w:sz w:val="22"/></w:rPr><w:t>8 Days / 7 Nights  (30 Sep 2026 – 07 Oct 2026)</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Row 2: Route -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Curated Route</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
          <w:p><w:r><w:rPr><w:color w:val="11130F"/><w:sz w:val="22"/></w:rPr><w:t>{xml_escape(ctx.get('route_txt') or 'Sapa – Hanoi – Ninh Binh – Halong Bay – Hanoi')}</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Row 3: Travelers -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Travel Party</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
          <w:p><w:r><w:rPr><w:color w:val="11130F"/><w:sz w:val="22"/></w:rPr><w:t>5 Adults (1 Double Room + 1 Triple Room) · Indian Market</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Row 4: Hotel Tier -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Accommodation Tier</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
          <w:p><w:r><w:rPr><w:color w:val="11130F"/><w:sz w:val="22"/></w:rPr><w:t>Premium 4★ Luxury Mountain &amp; City Boutique Hotels + 5★ Luxury Halong Cruise</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Row 5: Dining & Dietary -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Dietary Preference</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
          <w:p><w:r><w:rPr><w:color w:val="11130F"/><w:b/><w:sz w:val="22"/></w:rPr><w:t>Indian Vegetarian (Lacto-Ovo: Eggs allowed, strictly no meat, fish, or seafood)</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Row 6: Style -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Travel Style</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
          <w:p><w:r><w:rPr><w:color w:val="11130F"/><w:sz w:val="22"/></w:rPr><w:t>100% Private luxury vehicle, dedicated English guide, 2 private 4-berth sleeper train cabins</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:pPr><w:spacing w:before="180" w:after="120"/></w:pPr></w:p>
    """)

    # 4. BEHIND THE CURATION (4 PILLARS)
    pillars = [
        ("Private & Flexible Pacing", "Travel in complete exclusivity with your private air-conditioned vehicle and dedicated English-speaking guide. Daily pacing is highly flexible, ensuring your group can explore Sapa, Hanoi, Ninh Binh, and Halong Bay comfortably at your own speed."),
        ("Carefully Curated Accommodations & Transport", "Enjoy premium accommodations including Sapa Jade Hill, Hanoi Le Jardin Hotel & Spa, and Ambassador Signature Cruise. For the overnight train back to Hanoi, we have pre-arranged 2 private 4-berth cabins on the Chapa Express Train to guarantee absolute privacy and space for your 5 guests."),
        ("Dedicated Indian Vegetarian Dietary Care", "Your dietary requirements are fully respected. All included meals feature carefully curated Indian vegetarian selections (eggs permitted, strictly no meat/seafood). Restaurants and cruise chefs are briefed to prevent cross-contamination."),
        ("Balanced Highlights of Northern Vietnam", "A perfect harmony of highland exploration in Sapa, historic culture in Hanoi, scenic rivers in Ninh Binh, and a luxury overnight cruise in Halong Bay, offering a complete northern Vietnam experience in 8 days.")
    ]

    body_xml_parts.append("""
    <!-- SECTION HEADING: BEHIND THE CURATION -->
    <w:p>
      <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>Behind the Itinerary Curation</w:t>
      </w:r>
    </w:p>
    """)

    for title, desc in pillars:
        body_xml_parts.append(f"""
        <w:tbl>
          <w:tblPr>
            <w:tblW w:w="9740" w:type="dxa"/>
            <w:tblBorders>
              <w:top w:val="single" w:sz="4" w:color="E5D5BA"/>
              <w:left w:val="single" w:sz="18" w:color="CBA135"/>
              <w:bottom w:val="single" w:sz="4" w:color="E5D5BA"/>
              <w:right w:val="single" w:sz="4" w:color="E5D5BA"/>
            </w:tblBorders>
            <w:tblCellMar>
              <w:top w:w="120" w:type="dxa"/>
              <w:bottom w:w="120" w:type="dxa"/>
              <w:left w:w="180" w:type="dxa"/>
              <w:right w:w="180" w:type="dxa"/>
            </w:tblCellMar>
          </w:tblPr>
          <w:tr>
            <w:tc>
              <w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/></w:tcPr>
              <w:p>
                <w:pPr><w:spacing w:before="40" w:after="60"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                    <w:color w:val="17412E"/>
                    <w:b/>
                    <w:sz w:val="26"/>
                  </w:rPr>
                  <w:t>{xml_escape(title)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="0" w:after="60"/><w:jc w:val="both"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                    <w:color w:val="333333"/>
                    <w:sz w:val="22"/>
                  </w:rPr>
                  <w:t>{xml_escape(desc)}</w:t>
                </w:r>
              </w:p>
            </w:tc>
          </w:tr>
        </w:tbl>
        <w:p><w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr></w:p>
        """)

    # 5. DAY-BY-DAY JOURNEY PROGRAM (8 DAYS)
    itinerary_days = ctx.get("itinerary") or []
    day_images_map = {
        1: fansipan_rid,
        2: jade_rid,
        3: fansipan_rid,
        4: train_rid,
        5: jardin_rid,
        6: tamcoc_rid,
        7: halong_rid,
        8: hero_rid,
    }

    body_xml_parts.append("""
    <!-- SECTION HEADING: DAY-BY-DAY ITINERARY -->
    <w:p>
      <w:pPr><w:spacing w:before="360" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>Day-by-Day Journey Program</w:t>
      </w:r>
    </w:p>
    """)

    for day in itinerary_days:
        day_num = day.get("dayNumber")
        day_date = day.get("date") or ""
        day_title = day.get("title") or f"Day {day_num}"
        descs = day.get("description") or []
        full_desc = " ".join(descs)
        overnight = day.get("overnight") or ""
        meals = ", ".join(day.get("meals") or [])
        activities = " ".join(day.get("activities") or [])

        img_rid = day_images_map.get(day_num)
        img_xml = create_drawing_xml(img_rid, 2.2, 1.5, f"Day {day_num} Picture") if img_rid else ""

        body_xml_parts.append(f"""
        <!-- DAY {day_num} CARD -->
        <w:tbl>
          <w:tblPr>
            <w:tblW w:w="9740" w:type="dxa"/>
            <w:tblBorders>
              <w:top w:val="single" w:sz="12" w:color="17412E"/>
              <w:left w:val="single" w:sz="6" w:color="E5D5BA"/>
              <w:bottom w:val="single" w:sz="6" w:color="E5D5BA"/>
              <w:right w:val="single" w:sz="6" w:color="E5D5BA"/>
            </w:tblBorders>
            <w:tblCellMar>
              <w:top w:w="140" w:type="dxa"/>
              <w:bottom w:w="140" w:type="dxa"/>
              <w:left w:w="180" w:type="dxa"/>
              <w:right w:w="180" w:type="dxa"/>
            </w:tblCellMar>
          </w:tblPr>
          
          <!-- Header row -->
          <w:tr>
            <w:tc>
              <w:tcPr>
                <w:tcW w:w="9740" w:type="dxa"/>
                <w:gridSpan w:val="2"/>
                <w:shd w:val="clear" w:color="auto" w:fill="17412E"/>
              </w:tcPr>
              <w:p>
                <w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                    <w:color w:val="CBA135"/>
                    <w:b/>
                    <w:sz w:val="28"/>
                  </w:rPr>
                  <w:t>DAY {day_num} ({xml_escape(day_date)}) — {xml_escape(day_title.replace(f'Day {day_num} — ', ''))}</w:t>
                </w:r>
              </w:p>
            </w:tc>
          </w:tr>

          <!-- Content row -->
          <w:tr>
            <w:tc>
              <w:tcPr><w:tcW w:w="6800" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/></w:tcPr>
              <w:p>
                <w:pPr><w:spacing w:before="60" w:after="80"/><w:jc w:val="both"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                    <w:color w:val="11130F"/>
                    <w:sz w:val="22"/>
                  </w:rPr>
                  <w:t>{xml_escape(full_desc)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
                <w:r>
                  <w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="20"/></w:rPr>
                  <w:t>Meals: </w:t>
                </w:r>
                <w:r>
                  <w:rPr><w:color w:val="333333"/><w:sz w:val="20"/></w:rPr>
                  <w:t>{xml_escape(meals)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="0" w:after="40"/></w:pPr>
                <w:r>
                  <w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="20"/></w:rPr>
                  <w:t>Overnight: </w:t>
                </w:r>
                <w:r>
                  <w:rPr><w:color w:val="333333"/><w:sz w:val="20"/></w:rPr>
                  <w:t>{xml_escape(overnight)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="0" w:after="60"/></w:pPr>
                <w:r>
                  <w:rPr><w:b/><w:color w:val="CBA135"/><w:sz w:val="20"/></w:rPr>
                  <w:t>Included Services: </w:t>
                </w:r>
                <w:r>
                  <w:rPr><w:color w:val="333333"/><w:sz w:val="20"/></w:rPr>
                  <w:t>{xml_escape(activities)}</w:t>
                </w:r>
              </w:p>
            </w:tc>
            <w:tc>
              <w:tcPr><w:tcW w:w="2940" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/><w:vAlign w:val="center"/></w:tcPr>
              <w:p><w:pPr><w:jc w:val="center"/></w:pPr>{img_xml}</w:p>
            </w:tc>
          </w:tr>
        </w:tbl>
        <w:p><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr></w:p>
        """)

    # 6. SELECTED HOTEL PLAN (4 PROPERTIES)
    hotels = ctx.get("hotels") or []
    hotel_img_rids = [jade_rid, train_rid, jardin_rid, cruise_rid]

    body_xml_parts.append("""
    <!-- SECTION HEADING: SELECTED HOTEL PLAN -->
    <w:p>
      <w:pPr><w:spacing w:before="360" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>Selected Luxury Hotel &amp; Overnight Plan</w:t>
      </w:r>
    </w:p>
    """)

    for idx, hotel in enumerate(hotels):
        h_name = hotel.get("name") or ""
        h_city = hotel.get("city_country") or ""
        h_intro = hotel.get("introduction") or ""
        h_dates = hotel.get("date_range") or ""
        h_tel = hotel.get("tel") or ""

        h_img_rid = hotel_img_rids[idx] if idx < len(hotel_img_rids) else None
        h_img_xml = create_drawing_xml(h_img_rid, 2.2, 1.5, f"{h_name} Photo") if h_img_rid else ""

        body_xml_parts.append(f"""
        <!-- HOTEL {idx+1} CARD -->
        <w:tbl>
          <w:tblPr>
            <w:tblW w:w="9740" w:type="dxa"/>
            <w:tblBorders>
              <w:top w:val="single" w:sz="12" w:color="CBA135"/>
              <w:left w:val="single" w:sz="6" w:color="E5D5BA"/>
              <w:bottom w:val="single" w:sz="6" w:color="E5D5BA"/>
              <w:right w:val="single" w:sz="6" w:color="E5D5BA"/>
            </w:tblBorders>
            <w:tblCellMar>
              <w:top w:w="140" w:type="dxa"/>
              <w:bottom w:w="140" w:type="dxa"/>
              <w:left w:w="180" w:type="dxa"/>
              <w:right w:w="180" w:type="dxa"/>
            </w:tblCellMar>
          </w:tblPr>
          <w:tr>
            <w:tc>
              <w:tcPr><w:tcW w:w="6800" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/></w:tcPr>
              <w:p>
                <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                    <w:color w:val="CBA135"/>
                    <w:b/>
                    <w:sz w:val="18"/>
                  </w:rPr>
                  <w:t>{xml_escape(h_city.upper())}  ·  {xml_escape(h_dates)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="0" w:after="60"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
                    <w:color w:val="17412E"/>
                    <w:b/>
                    <w:sz w:val="28"/>
                  </w:rPr>
                  <w:t>{xml_escape(h_name)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="0" w:after="60"/><w:jc w:val="both"/></w:pPr>
                <w:r>
                  <w:rPr>
                    <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
                    <w:color w:val="333333"/>
                    <w:sz w:val="20"/>
                  </w:rPr>
                  <w:t>{xml_escape(h_intro)}</w:t>
                </w:r>
              </w:p>
              <w:p>
                <w:pPr><w:spacing w:before="0" w:after="40"/></w:pPr>
                <w:r>
                  <w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="18"/></w:rPr>
                  <w:t>Phone: </w:t>
                </w:r>
                <w:r>
                  <w:rPr><w:color w:val="706A5D"/><w:sz w:val="18"/></w:rPr>
                  <w:t>{xml_escape(h_tel)}</w:t>
                </w:r>
              </w:p>
            </w:tc>
            <w:tc>
              <w:tcPr><w:tcW w:w="2940" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/><w:vAlign w:val="center"/></w:tcPr>
              <w:p><w:pPr><w:jc w:val="center"/></w:pPr>{h_img_xml}</w:p>
            </w:tc>
          </w:tr>
        </w:tbl>
        <w:p><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr></w:p>
        """)

    # 7. JOURNEY INVESTMENT & COMMERCIAL PRICING
    body_xml_parts.append("""
    <!-- SECTION HEADING: JOURNEY INVESTMENT -->
    <w:p>
      <w:pPr><w:spacing w:before="360" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>Journey Investment</w:t>
      </w:r>
    </w:p>

    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="9740" w:type="dxa"/>
        <w:tblBorders>
          <w:top w:val="single" w:sz="12" w:color="CBA135"/>
          <w:left w:val="none"/>
          <w:bottom w:val="single" w:sz="12" w:color="CBA135"/>
          <w:right w:val="none"/>
          <w:insideH w:val="single" w:sz="4" w:color="E5D5BA"/>
          <w:insideV w:val="none"/>
        </w:tblBorders>
        <w:tblCellMar>
          <w:top w:w="160" w:type="dxa"/>
          <w:bottom w:w="160" w:type="dxa"/>
          <w:left w:w="200" w:type="dxa"/>
          <w:right w:w="200" w:type="dxa"/>
        </w:tblCellMar>
      </w:tblPr>
      
      <!-- Table Header -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="4800" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="17412E"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="22"/></w:rPr><w:t>Package Category</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="2500" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="17412E"/><w:jc w:val="right"/></w:tcPr>
          <w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="22"/></w:rPr><w:t>Per Person (USD)</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="2440" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="17412E"/><w:jc w:val="right"/></w:tcPr>
          <w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="22"/></w:rPr><w:t>Total Package (USD)</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Row 1 -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="4800" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/></w:tcPr>
          <w:p>
            <w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="22"/></w:rPr><w:t>Premium Accommodations &amp; Cruise (5 Adults)</w:t></w:r>
          </w:p>
          <w:p>
            <w:r><w:rPr><w:color w:val="706A5D"/><w:sz w:val="18"/></w:rPr><w:t>Twin/Double/Triple sharing basis (1 Double Room + 1 Triple Room)</w:t></w:r>
          </w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="2500" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/><w:vAlign w:val="center"/></w:tcPr>
          <w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="CBA135"/><w:sz w:val="26"/></w:rPr><w:t>$1,250</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="2440" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/><w:vAlign w:val="center"/></w:tcPr>
          <w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="28"/></w:rPr><w:t>$6,250</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:pPr><w:spacing w:before="60" w:after="180"/></w:pPr>
      <w:r><w:rPr><w:i/><w:color w:val="706A5D"/><w:sz w:val="18"/></w:rPr><w:t>* Rates are B2B net indicative and subject to reconfirmation at the time of deposit receipt.</w:t></w:r>
    </w:p>
    """)

    # 8. WHAT YOUR JOURNEY INCLUDES & NOT INCLUDED (2 COLUMNS)
    inclusions = ctx.get("inclusions") or []
    exclusions = ctx.get("exclusions") or []

    body_xml_parts.append("""
    <!-- SECTION HEADING: INCLUSIONS & EXCLUSIONS -->
    <w:p>
      <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>What Your Journey Includes</w:t>
      </w:r>
    </w:p>

    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="9740" w:type="dxa"/>
        <w:tblBorders>
          <w:top w:val="single" w:sz="12" w:color="17412E"/>
          <w:left w:val="single" w:sz="6" w:color="E5D5BA"/>
          <w:bottom w:val="single" w:sz="6" w:color="E5D5BA"/>
          <w:right w:val="single" w:sz="6" w:color="E5D5BA"/>
          <w:insideV w:val="single" w:sz="6" w:color="E5D5BA"/>
        </w:tblBorders>
        <w:tblCellMar>
          <w:top w:w="140" w:type="dxa"/>
          <w:bottom w:w="140" w:type="dxa"/>
          <w:left w:w="180" w:type="dxa"/>
          <w:right w:w="180" w:type="dxa"/>
        </w:tblCellMar>
      </w:tblPr>
      
      <!-- Headers -->
      <w:tr>
        <w:tc>
          <w:tcPr><w:tcW w:w="4870" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="17412E"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="22"/></w:rPr><w:t>Included in Your Package</w:t></w:r></w:p>
        </w:tc>
        <w:tc>
          <w:tcPr><w:tcW w:w="4870" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="706A5D"/></w:tcPr>
          <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="22"/></w:rPr><w:t>Not Included</w:t></w:r></w:p>
        </w:tc>
      </w:tr>

      <!-- Content -->
      <w:tr>
        <!-- Inclusions Column -->
        <w:tc>
          <w:tcPr><w:tcW w:w="4870" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="FFFAF1"/></w:tcPr>
    """)

    for inc in inclusions:
        body_xml_parts.append(f"""
          <w:p>
            <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
            <w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="20"/></w:rPr><w:t>✓  </w:t></w:r>
            <w:r><w:rPr><w:color w:val="333333"/><w:sz w:val="20"/></w:rPr><w:t>{xml_escape(inc)}</w:t></w:r>
          </w:p>
        """)

    body_xml_parts.append("""
        </w:tc>
        <!-- Exclusions Column -->
        <w:tc>
          <w:tcPr><w:tcW w:w="4870" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
    """)

    for exc in exclusions:
        body_xml_parts.append(f"""
          <w:p>
            <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
            <w:r><w:rPr><w:b/><w:color w:val="999999"/><w:sz w:val="20"/></w:rPr><w:t>—  </w:t></w:r>
            <w:r><w:rPr><w:color w:val="666666"/><w:sz w:val="20"/></w:rPr><w:t>{xml_escape(exc)}</w:t></w:r>
          </w:p>
        """)

    body_xml_parts.append("""
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:pPr><w:spacing w:before="180" w:after="120"/></w:pPr></w:p>
    """)

    # 9. BOOKING TERMS & PAYMENT POLICIES
    terms = [
        ("Deposit", "A 30% deposit is required at the time of booking to secure hotels, cruise, and train cabins."),
        ("Balance Payment", "The remaining 70% balance is due 30 days prior to arrival in Vietnam."),
        ("Cancellation Policy", "Free cancellation up to 45 days prior to departure. 50% cancellation fee applies between 44 and 15 days."),
        ("Confirmation", "Subject to room availability. Final confirmations will be sent within 24 hours of deposit receipt.")
    ]

    body_xml_parts.append("""
    <!-- SECTION HEADING: BOOKING TERMS -->
    <w:p>
      <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="17412E"/>
          <w:b/>
          <w:sz w:val="36"/>
        </w:rPr>
        <w:t>Booking &amp; Payment Terms</w:t>
      </w:r>
    </w:p>

    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="9740" w:type="dxa"/>
        <w:tblBorders>
          <w:top w:val="single" w:sz="6" w:color="D8BD85"/>
          <w:left w:val="none"/>
          <w:bottom w:val="single" w:sz="6" w:color="D8BD85"/>
          <w:right w:val="none"/>
          <w:insideH w:val="single" w:sz="4" w:color="E5D5BA"/>
          <w:insideV w:val="none"/>
        </w:tblBorders>
        <w:tblCellMar>
          <w:top w:w="100" w:type="dxa"/>
          <w:bottom w:w="100" w:type="dxa"/>
          <w:left w:w="160" w:type="dxa"/>
          <w:right w:w="160" w:type="dxa"/>
        </w:tblCellMar>
      </w:tblPr>
    """)

    for term_title, term_body in terms:
        body_xml_parts.append(f"""
        <w:tr>
          <w:tc>
            <w:tcPr><w:tcW w:w="2600" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F9F6F0"/></w:tcPr>
            <w:p><w:r><w:rPr><w:b/><w:color w:val="17412E"/><w:sz w:val="20"/></w:rPr><w:t>{xml_escape(term_title)}</w:t></w:r></w:p>
          </w:tc>
          <w:tc>
            <w:tcPr><w:tcW w:w="7140" w:type="dxa"/></w:tcPr>
            <w:p><w:r><w:rPr><w:color w:val="333333"/><w:sz w:val="20"/></w:rPr><w:t>{xml_escape(term_body)}</w:t></w:r></w:p>
          </w:tc>
        </w:tr>
        """)

    body_xml_parts.append("""
    </w:tbl>
    
    <!-- FOOTER NOTE -->
    <w:p><w:pPr><w:spacing w:before="360" w:after="120"/><w:jc w:val="center"/></w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Cormorant Garamond" w:hAnsi="Cormorant Garamond" w:cs="Georgia"/>
          <w:color w:val="CBA135"/>
          <w:i/>
          <w:b/>
          <w:sz w:val="24"/>
        </w:rPr>
        <w:t>Thank you for choosing Capella Travel · Crafted with passion for Anisha's Family</w:t>
      </w:r>
    </w:p>
    """)

    # OpenXML Assembly
    full_body = "".join(body_xml_parts)

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
            xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    {full_body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    # [Content_Types].xml
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Default Extension="jpg" ContentType="image/jpeg"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="webp" ContentType="image/webp"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    # _rels/.rels
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    # word/_rels/document.xml.rels
    rel_lines = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    ]
    for r_id, target in image_rels:
        rel_lines.append(
            f'<Relationship Id="{r_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>'
        )

    doc_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {"".join(rel_lines)}
</Relationships>"""

    # word/styles.xml
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Montserrat" w:hAnsi="Montserrat" w:cs="Calibri"/>
        <w:color w:val="11130F"/>
        <w:sz w:val="22"/>
        <w:lang w:val="en-US"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>"""

    # Output paths
    out_paths = [
        os.path.join(repo_root, "published", quotation_id, "quotation_anisha.docx"),
        os.path.join(repo_root, "quote-generator", "public", "published", quotation_id, "quotation_anisha.docx"),
    ]

    for out_path in out_paths:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("word/_rels/document.xml.rels", doc_rels)
            zf.writestr("word/document.xml", document_xml)
            zf.writestr("word/styles.xml", styles_xml)

            # Write embedded media files
            for img_info in images_to_embed.values():
                zf.writestr(f"word/media/{img_info['media_name']}", img_info["bytes"])

        print(f"✓ Generated {out_path} ({os.path.getsize(out_path)} bytes, {len(images_to_embed)} images embedded)")


if __name__ == "__main__":
    main()

import re

with open("generate_sara_2pax_quotation.py", "r", encoding="utf-8") as f:
    content = f.read()

# We want to change the part after quotation generated to set the template
replacement = """
        # Force prototype theme
        from main import quotations
        if quotation_id in quotations:
            if "ctx" not in quotations[quotation_id]:
                quotations[quotation_id]["ctx"] = {}
            quotations[quotation_id]["ctx"]["template_name"] = "prototype_itinerary_imagery.html"
            if "html" in quotations[quotation_id]:
                del quotations[quotation_id]["html"]
        
        # Verify get endpoint and save HTML
"""

content = content.replace("        # Verify get endpoint and save HTML", replacement)

with open("generate_prototype.py", "w", encoding="utf-8") as f:
    f.write(content)

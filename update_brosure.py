with open("templates/vietnam_luxury_brosure.html", "r", encoding="utf-8") as f:
    content = f.read()

old_span = """        <span class="template-text" style="font-weight:600;">{% if template_name == 'vietnam_heritage_luxury.html'
          %}Heritage Theme{% else %}Brochure Theme{% endif %}</span>"""

new_span = """        <span class="template-text" style="font-weight:600;">{% if template_name == 'vietnam_heritage_luxury.html'
          %}Heritage Theme{% elif template_name == 'prototype_itinerary_imagery.html' %}Prototype Theme{% else %}Brochure Theme{% endif %}</span>"""

content = content.replace(old_span, new_span)

import re
modal_pattern = re.compile(r'<!-- Custom Theme Selector Modal -->.*?<!-- Custom Confirmation Modal for Theme Switch -->', re.DOTALL)

new_modal = """<!-- Custom Theme Selector Modal -->
  <div id="template-modal" class="pb-modal-overlay" onclick="closeTemplateModal(event)">
    <div class="pb-modal-card" onclick="event.stopPropagation()">
      <div class="pb-modal-header">
        <h3>Select Theme</h3>
        <button class="pb-modal-close" onclick="closeTemplateModal(event)">&times;</button>
      </div>
      <div class="pb-domain-list">
        <div class="pb-domain-item {% if template_name == 'vietnam_luxury_brosure.html' %}active{% endif %}"
          onclick="promptSwitchTemplate('vietnam_luxury_brosure.html')"
          style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; cursor:pointer; border-bottom:1px solid rgba(0,0,0,0.05);">
          <div style="display:flex; align-items:center; gap:12px;">
            <div class="pb-domain-details">
              <div class="pb-domain-name" style="font-weight:600; font-size:14px; text-align:left;">Brochure Theme</div>
              <div class="pb-domain-badge prod" style="font-size:11px; color:#666;">Modern & visual layout</div>
            </div>
          </div>
          {% if template_name == 'vietnam_luxury_brosure.html' %}
          <div style="color: #4CAF50;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          {% endif %}
        </div>
        <div class="pb-domain-item {% if template_name == 'vietnam_heritage_luxury.html' %}active{% endif %}"
          onclick="promptSwitchTemplate('vietnam_heritage_luxury.html')"
          style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; cursor:pointer; border-bottom:1px solid rgba(0,0,0,0.05);">
          <div style="display:flex; align-items:center; gap:12px;">
            <div class="pb-domain-details">
              <div class="pb-domain-name" style="font-weight:600; font-size:14px; text-align:left;">Heritage Theme</div>
              <div class="pb-domain-badge prod" style="font-size:11px; color:#666;">Classic & structured layout</div>
            </div>
          </div>
          {% if template_name == 'vietnam_heritage_luxury.html' %}
          <div style="color: #4CAF50;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          {% endif %}
        </div>
        <div class="pb-domain-item {% if template_name == 'prototype_itinerary_imagery.html' %}active{% endif %}"
          onclick="promptSwitchTemplate('prototype_itinerary_imagery.html')"
          style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; cursor:pointer; border-bottom:1px solid rgba(0,0,0,0.05);">
          <div style="display:flex; align-items:center; gap:12px;">
            <div class="pb-domain-details">
              <div class="pb-domain-name" style="font-weight:600; font-size:14px; text-align:left;">Prototype Theme</div>
              <div class="pb-domain-badge prod" style="font-size:11px; color:#666;">Itinerary with Imagery</div>
            </div>
          </div>
          {% if template_name == 'prototype_itinerary_imagery.html' %}
          <div style="color: #4CAF50;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>

  <!-- Custom Confirmation Modal for Theme Switch -->"""

content = modal_pattern.sub(new_modal, content)

with open("templates/vietnam_luxury_brosure.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated vietnam_luxury_brosure.html")

import re

template_path = "templates/vietnam_luxury_brosure.html"

with open(template_path, "r") as f:
    content = f.read()

replacement = """    <section id="itinerary">
      <style>
      /* CSS from styles.css */
      .chapter { margin-bottom: 140px; }
      .chapter-opening { position: relative; min-height: 68svh; display: flex; align-items: end; overflow: hidden; color: #faf8f3; }
      .chapter-opening::before { content: ""; position: absolute; inset: 0; background-image: var(--chapter-image); background-position: center; background-size: cover; }
      .chapter-opening::after { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(23,37,31,.06), rgba(23,37,31,.78)); }
      .chapter-opening-content { position: relative; z-index: 2; padding-block: 80px; padding-inline: 48px; }
      .chapter-number { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; }
      .chapter-opening h3 { max-width: 800px; margin: 10px 0 0; font-family: "Cormorant Garamond", Georgia, serif; font-size: clamp(64px, 9vw, 126px); font-weight: 400; line-height: 0.9; letter-spacing: -0.03em; }
      .chapter-opening p { max-width: 620px; margin: 24px 0 0; font-family: "Cormorant Garamond", Georgia, serif; font-size: 23px; line-height: 1.35; }
      .chapter-days { width: min(calc(100% - 128px), 1380px); margin-inline: auto; padding-top: 90px; }
      .day { position: relative; margin-bottom: 110px; }
      .day-kicker { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; margin-bottom: 18px; color: #66685f; font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; }
      .day-kicker .destination { color: #24382f; font-weight: 600; }
      .day-title { margin: 0; font-family: "Cormorant Garamond", Georgia, serif; font-size: clamp(42px, 5vw, 74px); font-weight: 500; line-height: 0.98; letter-spacing: -0.02em; }
      .day-copy { max-width: 650px; color: #66685f; font-size: 17px; line-height: 1.75; }
      .day-image { min-height: 320px; background-image: var(--image); background-position: center; background-size: cover; background-color: #d8d0c2; }
      .day-image.hero-image { min-height: 620px; }
      .day-image.small-image { min-height: 270px; }
      .day-detail-list { display: grid; gap: 12px; margin: 30px 0 0; padding: 22px 0 0; border-top: 1px solid #d8d0c2; }
      .day-detail { display: grid; grid-template-columns: 130px 1fr; gap: 24px; font-size: 13px; }
      .day-detail dt { color: #66685f; margin:0;}
      .day-detail dd { margin: 0; }
      .logic-chip { display: none; width: max-content; margin-top: 18px; padding: 5px 9px; color: #24382f; border: 1px solid #aebdb8; border-radius: 0; background: rgba(174, 189, 184, 0.12); font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; }
      
      .layout-arrival { display: grid; grid-template-columns: 1fr 1.1fr; gap: 8vw; align-items: center; }
      .layout-arrival .day-image { min-height: 720px; border-radius: 0; }
      .layout-transition { display: grid; grid-template-columns: 0.72fr 1.28fr; gap: 8vw; align-items: center; padding-block: 30px; }
      .layout-transition .day-copy-wrap { padding-left: 40px; border-left: 1px solid #a88c58; }
      .layout-transition .day-image { min-height: 460px; }
      .layout-exploration { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 42px; }
      .layout-exploration .editorial-copy { align-self: end; padding: 0 0 20px 10px; }
      .layout-exploration .supporting-images { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
      .layout-scenic .hero-image { min-height: 72svh; }
      .layout-scenic .scenic-copy { width: min(760px, calc(100% - 80px)); margin: -120px 0 0 auto; position: relative; z-index: 2; padding: 52px 58px; background: #f3efe6; }
      .layout-scenic .supporting-images { display: grid; grid-template-columns: 0.72fr 1.28fr; gap: 24px; margin-top: 36px; }
      .layout-cultural { display: grid; grid-template-columns: 0.84fr 1.16fr; gap: 44px; }
      .layout-cultural .portrait { min-height: 720px; }
      .layout-cultural .cultural-right { display: grid; align-content: end; gap: 28px; }
      .layout-cultural .supporting-images { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
      .layout-leisure { display: grid; grid-template-columns: 1.25fr 0.75fr; gap: 6vw; align-items: center; }
      .layout-leisure .day-copy-wrap { padding: 55px 0; }
      .layout-leisure .day-image { min-height: 580px; }
      .layout-departure { max-width: 880px; margin-inline: auto; padding: 80px 0 20px; text-align: center; border-top: 1px solid #d8d0c2; }
      .layout-departure .day-copy { margin-inline: auto; }
      
      @media (max-width: 980px) {
        .chapter-days { width: min(calc(100% - 48px), 1380px); }
        .layout-arrival, .layout-transition, .layout-exploration, .layout-cultural, .layout-leisure { grid-template-columns: 1fr; }
        .layout-arrival .day-image, .layout-cultural .portrait { min-height: 560px; }
        .layout-exploration .supporting-images { grid-column: auto; }
        .layout-scenic .scenic-copy { width: calc(100% - 32px); margin-top: -72px; padding: 36px; }
      }
      @media (max-width: 640px) {
        .chapter { margin-bottom: 90px; }
        .chapter-opening { min-height: 58svh; }
        .chapter-opening-content { padding-block: 52px; padding-inline: 24px; }
        .chapter-opening h3 { font-size: clamp(58px, 18vw, 88px); }
        .chapter-days { padding-top: 62px; width: 100%; padding-inline: 24px;}
        .day { margin-bottom: 82px; }
        .day-title { font-size: 38px; }
        .day-image.hero-image, .layout-scenic .hero-image { min-height: 480px; }
        .layout-exploration, .layout-cultural, .layout-leisure { gap: 28px; }
        .layout-exploration .supporting-images, .layout-cultural .supporting-images, .layout-scenic .supporting-images { grid-template-columns: 1fr; }
        .day-detail { grid-template-columns: 1fr; gap: 2px; }
        .layout-transition .day-copy-wrap { padding-left: 22px; }
      }
      </style>
      
      {% for chapter in chapters %}
      <div class="chapter" id="chapter-{{ chapter.chapterIndex }}">
        <header class="chapter-opening" style="--chapter-image: url('{{ chapter.days[0].layout_images.hero if chapter.days|length > 0 else '' }}');">
          <div class="chapter-opening-content">
            <div class="chapter-number">Chapter {{ chapter.chapterNumberStr }}</div>
            <h3>{{ chapter.destination }}</h3>
            {% if chapter.profile.chapterLine %}
            <p>{{ chapter.profile.chapterLine }}</p>
            {% endif %}
          </div>
        </header>

        <div class="chapter-days">
          {% for day in chapter.days %}
          {% set layout = day.layout_type %}
          {% set imgs = day.layout_images %}
          {% set day_idx_global = day.dayNumber %}
          
          <article class="day layout-{{ layout }}">
            {% if layout == 'arrival' %}
              <div class="day-copy-wrap">
                <div class="day-kicker">
                  <span class="destination">{{ chapter.destination }}</span>
                  <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
                </div>
                <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
                <div class="day-copy" style="margin-top:24px;">
                  {% for para in day.description %}
                  <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                  {% endfor %}
                </div>
                <dl class="day-detail-list">
                  {% if day.overnight %}
                  <div class="day-detail">
                    <dt>{{ "Overnight" | translate(lang) }}</dt>
                    <dd data-editable="day_overnight_{{ day_idx_global }}">{{ day.overnight | rtl_mixed(lang) }}</dd>
                  </div>
                  {% endif %}
                  {% if day.meals %}
                  <div class="day-detail">
                    <dt>{{ "Meals" | translate(lang) }}</dt>
                    <dd data-editable="day_meals_{{ day_idx_global }}">{{ (day.meals | join(' &middot; ')) | rtl_mixed(lang) }}</dd>
                  </div>
                  {% endif %}
                </dl>
                <div class="logic-chip">{{ layout }}</div>
              </div>
              <div class="day-image hero-image" style="--image: url('{{ imgs.hero }}')"></div>
              
            {% elif layout == 'transition' %}
              <div class="day-image" style="--image: url('{{ imgs.hero }}')"></div>
              <div class="day-copy-wrap">
                <div class="day-kicker">
                  <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
                </div>
                <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
                <div class="day-copy" style="margin-top:24px;">
                  {% for para in day.description %}
                  <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                  {% endfor %}
                </div>
                <dl class="day-detail-list">
                  {% if day.overnight %}
                  <div class="day-detail">
                    <dt>{{ "Overnight" | translate(lang) }}</dt>
                    <dd data-editable="day_overnight_{{ day_idx_global }}">{{ day.overnight | rtl_mixed(lang) }}</dd>
                  </div>
                  {% endif %}
                </dl>
                <div class="logic-chip">{{ layout }}</div>
              </div>

            {% elif layout == 'exploration' %}
              <div class="day-copy-wrap">
                <div class="day-kicker">
                  <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
                </div>
                <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
                <dl class="day-detail-list" style="margin-top:40px;">
                  {% if day.overnight %}
                  <div class="day-detail">
                    <dt>{{ "Overnight" | translate(lang) }}</dt>
                    <dd data-editable="day_overnight_{{ day_idx_global }}">{{ day.overnight | rtl_mixed(lang) }}</dd>
                  </div>
                  {% endif %}
                </dl>
                <div class="logic-chip">{{ layout }}</div>
              </div>
              <div class="editorial-copy day-copy">
                {% for para in day.description %}
                <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                {% endfor %}
              </div>
              <div class="supporting-images">
                <div class="day-image small-image" style="--image: url('{{ imgs['small-1'] }}')"></div>
                <div class="day-image small-image" style="--image: url('{{ imgs['small-2'] }}')"></div>
              </div>

            {% elif layout == 'scenic' %}
              <div style="grid-column: 1 / -1;">
                <div class="day-kicker">
                  <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
                </div>
                <div class="day-image hero-image" style="--image: url('{{ imgs.hero }}')"></div>
                <div class="scenic-copy">
                  <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
                  <div class="day-copy" style="margin-top:24px;">
                    {% for para in day.description %}
                    <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                    {% endfor %}
                  </div>
                  <dl class="day-detail-list">
                    {% if day.overnight %}
                    <div class="day-detail">
                      <dt>{{ "Overnight" | translate(lang) }}</dt>
                      <dd data-editable="day_overnight_{{ day_idx_global }}">{{ day.overnight | rtl_mixed(lang) }}</dd>
                    </div>
                    {% endif %}
                  </dl>
                  <div class="logic-chip">{{ layout }}</div>
                </div>
              </div>
              <div class="supporting-images" style="grid-column: 1 / -1;">
                <div class="day-image small-image" style="--image: url('{{ imgs['small-1'] }}')"></div>
                <div class="day-image small-image" style="--image: url('{{ imgs['small-2'] }}')"></div>
              </div>

            {% elif layout == 'cultural' %}
              <div class="day-image portrait" style="--image: url('{{ imgs.hero }}')"></div>
              <div class="cultural-right">
                <div class="day-copy-wrap">
                  <div class="day-kicker">
                    <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
                  </div>
                  <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
                  <div class="day-copy" style="margin-top:24px;">
                    {% for para in day.description %}
                    <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                    {% endfor %}
                  </div>
                  <dl class="day-detail-list">
                    {% if day.overnight %}
                    <div class="day-detail">
                      <dt>{{ "Overnight" | translate(lang) }}</dt>
                      <dd data-editable="day_overnight_{{ day_idx_global }}">{{ day.overnight | rtl_mixed(lang) }}</dd>
                    </div>
                    {% endif %}
                  </dl>
                  <div class="logic-chip">{{ layout }}</div>
                </div>
                <div class="supporting-images">
                  <div class="day-image small-image" style="--image: url('{{ imgs['small-1'] }}')"></div>
                  <div class="day-image small-image" style="--image: url('{{ imgs['small-2'] }}')"></div>
                </div>
              </div>

            {% elif layout == 'leisure' %}
              <div class="day-image" style="--image: url('{{ imgs.hero }}')"></div>
              <div class="day-copy-wrap">
                <div class="day-kicker">
                  <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
                </div>
                <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
                <div class="day-copy" style="margin-top:24px;">
                  {% for para in day.description %}
                  <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                  {% endfor %}
                </div>
                <div class="logic-chip">{{ layout }}</div>
              </div>

            {% elif layout == 'departure' %}
              <div class="day-kicker" style="justify-content: center;">
                <span>{{ "DAY" | translate(lang) }} {{ day.dayNumber }}</span>
              </div>
              <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
              <div class="day-copy" style="margin-top:24px;">
                {% for para in day.description %}
                <p data-editable="day_desc_{{ day_idx_global }}_{{ loop.index0 }}">{{ para | rtl_mixed(lang) }}</p>
                {% endfor %}
              </div>
              <div class="logic-chip">{{ layout }}</div>
              
            {% else %}
              <!-- Fallback -->
              <h4 class="day-title" data-editable="day_title_{{ day_idx_global }}">{{ day.title | rtl_mixed(lang) }}</h4>
              <div class="day-copy">
                {% for para in day.description %}
                <p>{{ para | rtl_mixed(lang) }}</p>
                {% endfor %}
              </div>
            {% endif %}
          </article>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </section>"""

# Using regex to find the itinerary section and replace it
# The itinerary section starts with <section id="itinerary"> and ends with </section>
pattern = r'<section id="itinerary">.*?</section>'
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(template_path, "w") as f:
    f.write(new_content)

print("Template updated successfully.")

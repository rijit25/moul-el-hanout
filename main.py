import json
import random
import math
from browser import document, window, timer, bind, html

# --- Global State ---
state = {
    "lang": "ar",
    "money": 100,
    "day": 1,
    "inventory": {
        "sardines": 10,
        "tea": 10,
        "oil": 5,
        "biscuits": 20,
        "water": 15
    },
    "prices": {
        "sardines": 5,
        "tea": 15,
        "oil": 20,
        "biscuits": 2,
        "water": 3
    },
    "emojis": {
        "sardines": "🐟",
        "tea": "☕",
        "oil": "🛢️",
        "biscuits": "🍪",
        "water": "💧"
    },
    "game_active": False,
    "loop_id": None,
    "customer_timer": 0,
    "thief_timer": 0,
    "max_stock": 10,
    "has_assistant": False,
    "has_calc": False,
    "assistant_tick": 0
}

audio_ctx = None
def play_sound(type):
    global audio_ctx
    if not window.AudioContext and not hasattr(window, 'webkitAudioContext'):
        return
    if audio_ctx is None:
        audio_ctx = window.AudioContext.new() if window.AudioContext else window.webkitAudioContext.new()
    
    if audio_ctx.state == 'suspended':
        audio_ctx.resume()
        
    osc = audio_ctx.createOscillator()
    gain = audio_ctx.createGain()
    osc.connect(gain)
    gain.connect(audio_ctx.destination)
    
    if type == "coin":
        osc.type = "sine"
        osc.frequency.setValueAtTime(1046.50, audio_ctx.currentTime)
        osc.frequency.exponentialRampToValueAtTime(1318.51, audio_ctx.currentTime + 0.1)
        gain.gain.setValueAtTime(0.5, audio_ctx.currentTime)
        gain.gain.exponentialRampToValueAtTime(0.01, audio_ctx.currentTime + 0.1)
        osc.start()
        osc.stop(audio_ctx.currentTime + 0.1)
    elif type == "error":
        osc.type = "sawtooth"
        osc.frequency.setValueAtTime(150, audio_ctx.currentTime)
        gain.gain.setValueAtTime(0.5, audio_ctx.currentTime)
        gain.gain.exponentialRampToValueAtTime(0.01, audio_ctx.currentTime + 0.2)
        osc.start()
        osc.stop(audio_ctx.currentTime + 0.2)

def show_floating_text(text, x, y):
    div = html.DIV(text, Class="floating-text")
    div.style.left = f"{x}px"
    div.style.top = f"{y}px"
    document["game-container"] <= div
    timer.set_timeout(lambda: div.remove(), 1000)

translations = {}
current_customer = None

# --- Localization System ---
def load_language(lang):
    state["lang"] = lang
    document.documentElement.className = "rtl" if lang == "ar" else "ltr"
    
    # In a real deployed environment, fetch using window.fetch
    # For local Brython without server, we simulate loading the JSON using XHR
    req = window.XMLHttpRequest.new()
    req.open("GET", f"lang/{lang}.json", False)
    req.send()
    
    global translations
    translations = json.loads(req.responseText)
    
    # Save selection
    window.localStorage.setItem("hanout_lang", lang)
    update_ui_texts()

def t(key, *args):
    """Translate key and optionally format with args"""
    text = translations.get(key, key)
    if args:
        # Simple formatting
        for arg in args:
            text = text.replace("{}", str(arg), 1)
    return text

def update_ui_texts():
    # Update elements with data-t attribute
    for el in document.querySelectorAll("[data-t]"):
        key = el.attrs["data-t"]
        el.text = t(key)
    
    # Update title
    document["t-title"].text = "Moul El Hanout" if state["lang"] == "fr" else "مول الحانوت"
    
    # Update dynamic HUD
    update_hud()

# --- Screens & UI ---
def show_screen(screen_id):
    for s in document.querySelectorAll(".screen"):
        s.classList.add("hidden")
    document[screen_id].classList.remove("hidden")

def show_notification(msg):
    div = html.DIV(msg, Class="notification")
    document["notifications"] <= div
    # Remove after animation
    timer.set_timeout(lambda: div.remove(), 2000)

def show_modal(title, text, input_needed=False, on_submit=None, buttons=None):
    document["modal"].classList.remove("hidden")
    document["modal-title"].text = title
    document["modal-text"].text = text
    
    inp = document["modal-input"]
    if input_needed:
        inp.classList.remove("hidden")
        inp.value = ""
        inp.focus()
    else:
        inp.classList.add("hidden")
        
    btn_container = document["modal-buttons"]
    btn_container.clear()
    
    if buttons:
        for btn_text, callback in buttons:
            b = html.BUTTON(btn_text, Class="menu-btn")
            b.bind("click", callback)
            btn_container <= b

def close_modal(*args):
    document["modal"].classList.add("hidden")

# --- Game Logic ---
def update_hud():
    document["hud-money"].text = t("money", state["money"])
    document["hud-day"].text = t("day", state["day"])

def render_shelves():
    container = document["shelves"]
    container.clear()
    
    for item, count in state["inventory"].items():
        div = html.DIV(Class="product", id=f"prod-{item}")
        div <= html.DIV(state["emojis"][item], Class="emoji")
        div <= html.DIV(t("products").get(item, item), Class="name")
        div <= html.DIV(str(count), Class="stock", id=f"stock-{item}")
        div.bind("click", lambda ev, i=item: sell_item(i))
        container <= div

def sell_item(item):
    if not state["game_active"] or current_customer:
        return
        
    if state["inventory"][item] > 0:
        state["inventory"][item] -= 1
        state["money"] += state["prices"][item]
        document[f"stock-{item}"].text = str(state["inventory"][item])
        update_hud()
        play_sound("coin")
        
        # Get coordinates of the clicked item
        el = document[f"prod-{item}"]
        rect = el.getBoundingClientRect()
        show_floating_text(f"+{state['prices'][item]}", rect.left + 20, rect.top)
        
        window.localStorage.setItem("hanout_money", str(state["money"]))
        window.localStorage.setItem("hanout_inventory", json.dumps(state["inventory"]))
    else:
        play_sound("error")
        show_notification(t("sold_out"))

def render_assistant():
    if state["has_assistant"]:
        if not document.getElementById("assistant"):
            div = html.DIV("🧑‍🔧", id="assistant")
            document["customer-area"] <= div

# --- Customers & Math Challenges ---
def spawn_customer():
    global current_customer
    if current_customer or not state["game_active"]:
        return
        
    area = document["customer-area"]
    area.clear()
    
    faces = ["👨", "👩", "👴", "👵", "👦", "👧", "👳‍♂️"]
    face = random.choice(faces)
    
    customer_div = html.DIV(Class="customer")
    customer_div <= html.DIV(face, Class="face")
    
    quote = random.choice(translations["customer_quotes"])
    bubble = html.DIV(quote, Class="speech-bubble")
    customer_div <= bubble
    
    area <= customer_div
    
    # Generate Math Challenge
    challenge_type = random.choice(["change", "multiply"])
    
    if challenge_type == "change":
        total = random.randint(10, 150)
        given = random.choice([50, 100, 200])
        while given <= total:
            given = random.choice([50, 100, 200, 500])
        
        answer = given - total
        q_text = t("math_question_1", given, total)
    else:
        qty = random.randint(2, 5)
        price = random.randint(3, 20)
        total = qty * price
        answer = total
        q_text = t("math_question_2", qty, "منتج" if state["lang"]=="ar" else "produit", price)
        
    current_customer = {
        "div": customer_div,
        "answer": answer,
        "reward": random.randint(5, 20)
    }
    
    customer_div.bind("click", lambda ev: trigger_math(q_text, answer))

def trigger_math(question, answer):
    def check_answer(ev):
        val = document["modal-input"].value
        try:
            if int(val) == answer:
                play_sound("coin")
                show_notification(t("correct", current_customer["reward"]))
                state["money"] += current_customer["reward"]
                update_hud()
                close_modal()
                clear_customer()
            else:
                play_sound("error")
                show_notification(t("wrong"))
                close_modal()
                clear_customer()
        except ValueError:
            pass

    show_modal(
        t("shop"), 
        question, 
        input_needed=True, 
        buttons=[(t("submit"), check_answer)]
    )

def clear_customer():
    global current_customer
    if current_customer:
        current_customer["div"].remove()
        current_customer = None

# --- Events (Thieves) ---
def spawn_thief():
    area = document["customer-area"]
    
    thief_div = html.DIV(Class="customer thief")
    thief_div <= html.DIV("🦹", Class="face")
    
    bubble = html.DIV("...", Class="speech-bubble")
    thief_div <= bubble
    area <= thief_div
    
    show_notification(t("thief_alert"))
    
    def catch_thief(ev):
        thief_div.remove()
        n1 = random.randint(3, 15)
        n2 = random.randint(3, 15)
        q_text = f"{n1} * {n2} = ?"
        ans = n1 * n2
        
        def check_thief_ans(ev2):
            try:
                if int(document["modal-input"].value) == ans:
                    play_sound("coin")
                    show_notification("Hero!")
                else:
                    play_sound("error")
                    show_notification("Failed!")
            except:
                pass
            close_modal()
            
        show_modal(t("thief_caught"), q_text, True, buttons=[(t("submit"), check_thief_ans)])
    
    thief_div.bind("click", catch_thief)
    
    # Escape after 3 seconds if not caught (5 if calc upgrade)
    escape_time = 5000 if state["has_calc"] else 3000
    def escape():
        if document["customer-area"].contains(thief_div):
            thief_div.remove()
            state["money"] = max(0, state["money"] - 20)
            update_hud()
            play_sound("error")
            show_notification(t("thief_escaped"))
            
    timer.set_timeout(escape, escape_time)


# --- Core Game Loop ---
def game_tick():
    if not state["game_active"]:
        return
        
    state["customer_timer"] += 1
    state["thief_timer"] += 1
    
    # Random customer every 5-10 ticks
    if state["customer_timer"] > random.randint(5, 10):
        spawn_customer()
        state["customer_timer"] = 0
        
    # Random thief roughly every 30-50 ticks
    if state["thief_timer"] > random.randint(30, 50):
        spawn_thief()
        state["thief_timer"] = 0
        
    # Assistant Logic
    if state["has_assistant"]:
        state["assistant_tick"] += 1
        if state["assistant_tick"] >= 10:
            for item, count in state["inventory"].items():
                if count > 0:
                    state["inventory"][item] -= 1
                    state["money"] += state["prices"][item]
                    document[f"stock-{item}"].text = str(state["inventory"][item])
                    update_hud()
                    play_sound("coin")
                    ast = document.getElementById("assistant")
                    if ast:
                        ast.classList.add("working")
                        timer.set_timeout(lambda: ast.classList.remove("working"), 500)
                    break
            state["assistant_tick"] = 0

def start_game(*args):
    state["game_active"] = True
    show_screen("game-ui")
    document["global-footer"].classList.add("hidden")
    render_shelves()
    update_hud()
    
    if state["loop_id"] is None:
        state["loop_id"] = timer.set_interval(game_tick, 1000)
        
    # Tutorial
    show_modal("Tutorial", t("tutorial"), False, buttons=[(t("close"), close_modal)])

# --- Initialization & Bindings ---
@bind("#btn-ar", "click")
def select_ar(ev):
    load_language("ar")
    show_screen("main-menu")

@bind("#btn-fr", "click")
def select_fr(ev):
    load_language("fr")
    show_screen("main-menu")

@bind("#btn-start", "click")
def init_new_game(ev):
    # Reset state
    state["money"] = 100
    state["inventory"] = {k: 10 for k in state["inventory"]}
    start_game()

@bind("#btn-continue", "click")
def continue_game(ev):
    saved_money = window.localStorage.getItem("hanout_money")
    saved_inv = window.localStorage.getItem("hanout_inventory")
    saved_up = window.localStorage.getItem("hanout_upgrades")
    if saved_money:
        state["money"] = int(saved_money)
    if saved_inv:
        state["inventory"] = json.loads(saved_inv)
    if saved_up == "1":
        state["max_stock"] = 50
        state["has_assistant"] = True
        state["has_calc"] = True
        render_assistant()
    start_game()

@bind("#btn-menu", "click")
def go_menu(ev):
    state["game_active"] = False
    show_screen("main-menu")
    document["global-footer"].classList.remove("hidden")

@bind("#btn-stock", "click")
def open_stock_menu(ev):
    # Buy 5 of each for 20dh for demo simplicity
    def buy_stock_action(ev):
        if state["money"] >= 50:
            state["money"] -= 50
            for k in state["inventory"]:
                state["inventory"][k] = min(state["max_stock"], state["inventory"][k] + 5)
            render_shelves()
            update_hud()
            close_modal()
            play_sound("coin")
            show_notification("+ Stock!")
        else:
            play_sound("error")
            show_notification(t("not_enough_money"))
            
    show_modal(
        t("inventory"), 
        "Buy refill pack (-50 dh)", 
        False, 
        buttons=[(t("buy"), buy_stock_action), (t("close"), close_modal)]
    )

@bind("#btn-upgrades", "click")
def open_upgrades_menu(ev):
    def buy_upgrade_action(ev):
        if state["money"] >= 200:
            state["money"] -= 200
            state["max_stock"] = 50
            state["has_assistant"] = True
            state["has_calc"] = True
            window.localStorage.setItem("hanout_upgrades", "1")
            update_hud()
            close_modal()
            render_assistant()
            play_sound("coin")
            show_notification("تمت الترقية!" if state["lang"] == "ar" else "Amélioration réussie!")
        else:
            play_sound("error")
            show_notification(t("not_enough_money"))
            
    show_modal(
        t("upgrades"), 
        f"{t('fridge')} / {t('shelves')} / {t('camera')} (-200 dh)", 
        False, 
        buttons=[(t("buy"), buy_upgrade_action), (t("close"), close_modal)]
    )

def init():
    saved_lang = window.localStorage.getItem("hanout_lang")
    if saved_lang:
        load_language(saved_lang)
        show_screen("main-menu")
    else:
        show_screen("lang-screen")

# Run init
init()

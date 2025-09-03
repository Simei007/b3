import MetaTrader5 as mt5
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import threading
import time
import pyautogui
import os

# =======================
# ⚙️ CONFIGURAÇÕES
# =======================
symbol = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
NUM_BARS = 200
interval_ms = 1000  # 1 segundo
TEMPO_LIMITE = 60   # 1 minuto para limpeza

pastas_para_limpar = [
    r"C:\Program Files\MetaTrader 5\Logs",
    r"C:\Program Files\MetaTrader 5\Bases\MetaQuotes-Demo\history",
]

extensoes_seguras = ('.log', '.tmp', '.dat')

# =======================
# 🚀 INICIALIZAÇÃO MT5
# =======================
if not mt5.initialize():
    raise RuntimeError("Erro ao iniciar o MetaTrader 5")
if not mt5.symbol_select(symbol, True):
    mt5.shutdown()
    raise RuntimeError(f"Erro ao selecionar o símbolo {symbol}")

# =======================
# 📊 FUNÇÃO RSI
# =======================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =======================
# 🔄 THREAD DE DADOS
# =======================
latest_data = pd.DataFrame()

def fetch_data_loop():
    global latest_data
    while True:
        rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, NUM_BARS)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            latest_data = df.dropna().copy()
        time.sleep(interval_ms / 1000.0)

threading.Thread(target=fetch_data_loop, daemon=True).start()

# =======================
# 🧹 LIMPEZA DE ARQUIVOS
# =======================
for pasta in pastas_para_limpar:
    print(f"\nLimpando: {pasta}")
    for root, dirs, files in os.walk(pasta):
        for file in files:
            caminho_completo = os.path.join(root, file)
            try:
                tempo_modificacao = os.path.getmtime(caminho_completo)
                idade_em_segundos = time.time() - tempo_modificacao

                if file.endswith(extensoes_seguras) and idade_em_segundos > TEMPO_LIMITE:
                    os.remove(caminho_completo)
                    print(f"[OK] Removido: {file}")
                else:
                    print(f"[SKIP] Ignorado: {file}")
            except PermissionError:
                print(f"[LOCKED] Permissão negada: {file}")
            except Exception as e:
                print(f"[ERROR] Erro ao remover {file}: {e}")

# =======================
# 📈 FUNÇÕES DE CONTROLE DE POSIÇÃO
# =======================
def existe_posicao_aberta():
    return mt5.positions_total() > 0

def posicao_compra_ativa():
    posicoes = mt5.positions_get(symbol=symbol)
    if posicoes:
        for p in posicoes:
            if p.type == mt5.ORDER_TYPE_BUY:
                return True
    return False

def posicao_venda_ativa():
    posicoes = mt5.positions_get(symbol=symbol)
    if posicoes:
        for p in posicoes:
            if p.type == mt5.ORDER_TYPE_SELL:
                return True
    return False

# =======================
# 📈 GRÁFICO E CLIQUES
# =======================
fig, ax = plt.subplots(figsize=(12, 6))

def update(frame):
    ax.clear()

    if latest_data.empty or latest_data.shape[0] < 30:
        ax.set_title("Aguardando dados...")
        return

    times = latest_data['time']
    close = latest_data['close']
    rsi = compute_rsi(close)

    sinais_compra = (rsi < 30)
    sinais_venda = (rsi > 70)

    ax.plot(times, rsi, color='purple', label='RSI')
    ax.plot(times[sinais_compra], rsi[sinais_compra], 'go', label='Sinal Compra')
    ax.plot(times[sinais_venda], rsi[sinais_venda], 'ro', label='Sinal Venda')
    ax.axhline(70, color='red', linestyle='--')
    ax.axhline(30, color='green', linestyle='--')
    ax.set_xlim(times.iloc[0], times.iloc[-1])
    ax.set_ylim(0, 100)
    ax.set_ylabel("RSI")
    ax.set_title(f"{symbol} - RSI")
    ax.legend(loc='upper left')

    # Automação de clique com controle de posição
    if sinais_compra.iloc[-1]:
        if not existe_posicao_aberta():
            pyautogui.click(x=516, y=162)  # botão de compra
            print("[AUTO] Clique de compra realizado!")
        elif posicao_venda_ativa():
            pyautogui.click(x=516, y=162)  # fechar venda com compra
            print("[AUTO] Compra para encerrar venda realizada!")

    elif sinais_venda.iloc[-1]:
        if not existe_posicao_aberta():
            pyautogui.click(x=516, y=200)  # botão de venda
            print("[AUTO] Clique de venda realizado!")
        elif posicao_compra_ativa():
            pyautogui.click(x=516, y=200)  # fechar compra com venda
            print("[AUTO] Venda para encerrar compra realizada!")

ani = animation.FuncAnimation(fig, update, interval=interval_ms, blit=False)
plt.tight_layout()
plt.show()

# =======================
# 📴 FINALIZAÇÃO
# =======================
mt5.shutdown()
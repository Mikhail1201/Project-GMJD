# Guía sencilla y bitácora — ESP32 Monómeros

**Proyecto:** Monitoreo de Gas, Humedad y Temperatura en Monómeros S.A.
**Equipo:** Grupo 8 (Daniel, Miguel, Guillermo y Juan)
**Módulo:** Punto 2 - Simulación en Wokwi (20%)
**Plataforma:** Wokwi Simulator (MicroPython v1.28.0), simulable tanto en el navegador como en la extensión de Wokwi para VS Code
**Link Proyecto en Wokwi:** https://wokwi.com/projects/473198397793084417

---

## 1. ¿Qué hace este circuito?

Hicimos un pequeño sistema de seguridad para la fábrica de Monómeros. Su trabajo es vigilar todo el tiempo: qué tan caliente está el lugar (temperatura), cuánta humedad hay, si hay gases peligrosos en el aire (como amoníaco/gases combustibles), y en qué área de la planta se está midiendo.

El sistema hace estas tareas en un ciclo continuo:

1. **Mide y revisa:** lee la temperatura y humedad del sensor DHT22, y lee el gas de un sensor MQ-2 real simulado (`wokwi-gas-sensor`) por ADC — ya no es un número inventado por software, es una lectura de un componente de hardware simulado de verdad.
2. **Muestra los datos:** en la pantalla LCD muestra los números en vivo (temperatura, humedad y gas), o el número de área que se está tecleando.
3. **Activa alertas:** si todo está bien, prende el LED Verde. Si el gas pasa de 400 PPM o la temperatura pasa de 45°C, apaga el verde y prende el LED Rojo de alarma, y además registra una alerta en la base de datos.
4. **Deja elegir el área:** con un teclado matricial se puede escribir el `id_area` de la planta al que pertenecen las mediciones (por ejemplo, área 5 = Patio de Tanques), en vez de que quede fijo en el código.
5. **Envía los datos:** cada 5 segundos reúne todas las medidas y las manda por Wi-Fi al backend Flask, corriendo en la misma máquina donde está la simulación.

---

## 2. Tabla de conexiones paso a paso

| Pieza / componente | Pin de la pieza | Pin en el ESP32 | ¿Para qué sirve? |
|---|---|---|---|
| Pantalla LCD 16x2 (I2C) | GND | GND | Polo negativo (tierra). |
| Pantalla LCD 16x2 (I2C) | VCC | 5V / VIN | Le da energía eléctrica a la pantalla. |
| Pantalla LCD 16x2 (I2C) | SDA | Pin 21 | Envía las letras y números a la pantalla. |
| Pantalla LCD 16x2 (I2C) | SCL | Pin 22 | Sincroniza el envío de datos. |
| Sensor DHT22 | VCC (Pata 1) | 3V3 | Le da energía (3.3V) al sensor. |
| Sensor DHT22 | SDA (Pata 2) | Pin 15 | Envía los datos de temperatura y humedad. |
| Sensor DHT22 | GND (Pata 4) | GND | Polo negativo (tierra). |
| LED Verde (Seguro) | Ánodo | Pin 2 | El ESP32 manda corriente cuando no hay peligro. |
| LED Verde (Seguro) | Cátodo | GND | Polo negativo. |
| LED Rojo (Peligro) | Ánodo | Pin 4 | El ESP32 manda corriente cuando hay peligro. |
| LED Rojo (Peligro) | Cátodo | GND | Polo negativo. |
| Botón Azul (Modo LCD) | Pata 1 | Pin 18 | Avisa al ESP32 que queremos cambiar de pantalla. |
| Botón Azul (Modo LCD) | Pata 2 | GND | Cierra el circuito cuando lo hundimos. |
| Botón Amarillo (Envío) | Pata 1 | Pin 19 | Ordena al ESP32 enviar los datos ya mismo. |
| Botón Amarillo (Envío) | Pata 2 | GND | Cierra el circuito cuando lo hundimos. |
| **Sensor de Gas MQ-2** (`wokwi-gas-sensor`) | VCC | 3V3 | Energía del sensor. |
| **Sensor de Gas MQ-2** | GND | GND | Polo negativo. |
| **Sensor de Gas MQ-2** | AOUT | **Pin 34** (ADC1) | Salida analógica del gas; se lee con `machine.ADC`. |
| **Teclado matricial 4x4** (`wokwi-membrane-keypad`) | R1-R4 | Pines 5, 13, 14, 27 | Filas de la matriz (salidas digitales). |
| **Teclado matricial 4x4** | C1-C4 | Pines 26, 25, 33, 32 | Columnas de la matriz (entradas con pull-up interno). |

**Nota sobre los pines del sensor de gas y el teclado:** se eligieron a propósito en el bloque ADC1 (32-39) y GPIOs de uso general que **no entran en conflicto con el Wi-Fi** — los pines de ADC2 (0, 2, 4, 12-15, 25-27) no se pueden leer de forma confiable como *analógicos* mientras el Wi-Fi está activo, pero sí se pueden usar como entradas/salidas puramente digitales sin problema (por eso el teclado sí usa 25, 26 y 27 como pines digitales del teclado, mientras que el sensor de gas usa el 34, que es ADC1 puro).

---

## 3. Explicación sencilla del código (dividido en partes)

El código está en MicroPython, organizado en partes como si fueran trabajadores con tareas asignadas:

- **Parte 1 — El Conector de Wi-Fi (`NetworkManager`):** busca la red del simulador, se conecta y avisa cuando el ESP32 ya tiene acceso.

- **Parte 2 — El Lector de Sensores (`EnvironmentalSensors`):** lee el DHT22 (con un límite de 2 segundos entre lecturas — más rápido que eso, el sensor responde con datos inválidos sin avisar) y lee el sensor de gas MQ-2 por ADC. El gas ya **no** se inventa con números aleatorios: se lee de verdad, con una calibración de "línea base" que se auto-ajusta hacia abajo si el sensor deriva con el tiempo (ver la bitácora, sección 6, para el porqué).

- **Parte 3 — El Encargado de Luces y Pantalla (`UserInterfaceManager`):** escribe en el LCD (la vista normal de T/H/Gas, la de "ESTADO PLANTA", el número de área mientras se teclea, y la confirmación del área) y prende/apaga los LEDs según si hay alerta.

- **Parte 3.5 — El Selector de Área (`AreaSelector`):** escanea un teclado matricial 4x4. Se teclean 1-2 dígitos con el `id_area` y se confirma con `#`; `*` borra lo tecleado. Reemplaza lo que antes iba fijo en el código (`ID_AREA = 1`).

- **Parte 4 — El Cerebro Principal (`MonomerosController`):** el jefe de todo. En un ciclo continuo: pide datos a los sensores, escanea el teclado, actualiza pantalla y LEDs, revisa los botones, y cada 5 segundos manda el paquete de datos a la API (usando el área que esté activa en ese momento).

---

## 4. Cómo correrlo en la extensión de Wokwi para VS Code

Esto es nuevo respecto a la versión original: además de simularlo en el navegador (el link de arriba), el proyecto también corre con la **extensión oficial de Wokwi para VS Code**, que simula el ESP32 localmente y deja conectarlo directamente al backend Flask de tu propia máquina.

1. **Backend corriendo primero:** desde `Backend/`, con `flask --app app run --host=0.0.0.0 --port=8000` (importante: `0.0.0.0`, no solo `127.0.0.1`, para que el simulador pueda alcanzarlo).
2. **Abre la carpeta `ESP32/` como workspace** en VS Code (el archivo `wokwi.toml` debe quedar en la raíz de lo que abras).
3. Da **▶ Start Simulation** y espera al prompt `>>>` de MicroPython.
4. Sube el código con el script ya preparado:
   ```bash
   subir_y_correr.bat
   ```
   Esto copia `i2c_lcd.py` y `main.py` al sistema de archivos simulado (que **no persiste** entre reinicios — hay que repetirlo cada vez que reinicies la simulación) y reinicia el ESP32 para que arranque `main.py` solo.
5. En el código, la URL del backend usa el hostname especial `http://host.wokwi.internal:8000/api` — **no** `localhost`, porque dentro del simulador `localhost` apunta al propio ESP32, no a tu computador.

---

## 5. ¿Cómo explicarlo? (guión fácil)

**1. ¿Qué hicimos?**
"Profesor, creamos el circuito en Wokwi para monitorear en tiempo real la planta de Monómeros usando MicroPython en el ESP32, y lo conectamos a nuestro propio backend Flask."

**2. ¿Qué piezas usamos?**
"Usamos un ESP32, un sensor DHT22 para temperatura y humedad, un sensor de gas MQ-2 simulado leído por ADC, una pantalla LCD I2C, dos LEDs indicadores, dos pulsadores y un teclado matricial 4x4 para elegir el área de la planta."

**3. ¿Cómo funciona el sensor de gas?**
"Al principio lo simulábamos con números aleatorios porque pensábamos que Wokwi no tenía un sensor de gas interactivo, pero sí existe (`wokwi-gas-sensor`, un MQ-2). Lo agregamos de verdad: se lee por ADC y se calibra contra una línea base en 'aire limpio', igual que se calibraría un MQ-2 real."

**4. ¿Cómo funcionan las alertas y los botones?**
"Si el gas pasa de 400 PPM o la temperatura pasa de 45°C, se prende el LED rojo de emergencia y se registra una alerta en la base de datos. Con el botón azul cambiamos la pantalla a modo diagnóstico, y con el amarillo forzamos el envío inmediato."

**5. ¿Cómo se elige el área?**
"Con el teclado matricial: se teclea el número del área y se confirma con `#`. La pantalla muestra en vivo lo que se va tecleando, y al confirmar se ve un mensaje de 'ÁREA CONFIRMADA' antes de volver a la vista normal."

---

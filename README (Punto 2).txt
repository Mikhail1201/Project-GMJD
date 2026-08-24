================================================================================
GUÍA SENCILLA Y BITÁCORA - ESP32 MONÓMEROS
================================================================================
Proyecto: Monitoreo de Gas, Humedad y Temperatura en Monómeros S.A.
Equipo: Grupo 8 (Daniel, Miguel, Guillermo y Juan)
Módulo: Punto 2 - Simulación en Wokwi (20%)
Plataforma: Wokwi Simulator (MicroPython v1.28.0)
Link Proyecto en Wokwi: https://wokwi.com/projects/473198397793084417

--------------------------------------------------------------------------------
1. ¿QUÉ HACE ESTE CIRCUITO?
--------------------------------------------------------------------------------
Hicimos un pequeño sistema de seguridad para la fábrica de Monómeros. Su trabajo
es vigilar tres cosas todo el tiempo: qué tan caliente está el lugar (temperatura),
cuánta humedad hay y si hay gases peligrosos en el aire (como amoníaco).

Todo el tiempo, el sistema hace 4 tareas básicas:
1. Mide y revisa: Lee la temperatura y humedad del sensor DHT22 y calcula
   valores lógicos de gas para saber si la planta está segura.
2. Muestra los datos: En la pantalla LCD muestra los números en vivo (temperatura,
   humedad y gas).
3. Activa alertas: Si todo está bien, prende el LED Verde. Si el gas pasa de
   400 PPM o la temperatura pasa de 45°C, apaga el verde y prende el LED Rojo
   de alarma.
4. Envía los datos: Cada 5 segundos reúne todas las medidas y las manda por
   internet (Wi-Fi) a nuestra base de datos.

--------------------------------------------------------------------------------
2. TABLA DE CONEXIONES PASO A PASO
--------------------------------------------------------------------------------
PIEZA / COMPONENTE        | PIN DE LA PIEZA         | PIN EN EL ESP32 | ¿PARA QUÉ SIRVE?
--------------------------------------------------------------------------------
Pantalla LCD 16x2 (I2C)   | GND                     | GND             | Polo negativo (tierra).
Pantalla LCD 16x2 (I2C)   | VCC                     | 5V / VIN        | Le da energía eléctrica a la pantalla.
Pantalla LCD 16x2 (I2C)   | SDA                     | Pin 21          | Envía las letras y números a la pantalla.
Pantalla LCD 16x2 (I2C)   | SCL                     | Pin 22          | Sincroniza el envío de datos.
--------------------------------------------------------------------------------
Sensor DHT22              | VCC (Pata 1)            | 3V3             | Le da energía (3.3V) al sensor.
Sensor DHT22              | SDA (Pata 2)            | Pin 15          | Envía los datos de temperatura y humedad.
Sensor DHT22              | GND (Pata 4)            | GND             | Polo negativo (tierra).
--------------------------------------------------------------------------------
LED Verde (Seguro)        | Ánodo (Pata doblada)    | Pin 2           | El ESP32 manda corriente cuando no hay peligro.
LED Verde (Seguro)        | Cátodo (Pata recta)     | GND             | Polo negativo.
--------------------------------------------------------------------------------
LED Rojo (Peligro)        | Ánodo (Pata doblada)    | Pin 4           | El ESP32 manda corriente cuando hay peligro.
LED Rojo (Peligro)        | Cátodo (Pata recta)     | GND             | Polo negativo.
--------------------------------------------------------------------------------
Botón Azul (Modo LCD)     | Pata arriba izq. (1.l)  | Pin 18          | Avisa al ESP32 que queremos cambiar de pantalla.
Botón Azul (Modo LCD)     | Pata abajo izq. (2.l)   | GND             | Cierra el circuito cuando lo hundimos.
--------------------------------------------------------------------------------
Botón Amarillo (Envío)    | Pata arriba izq. (1.l)  | Pin 19          | Ordena al ESP32 enviar los datos ya mismo.
Botón Amarillo (Envío)    | Pata abajo izq. (2.l)   | GND             | Cierra el circuito cuando lo hundimos.
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
3. EXPLICACIÓN SENCILLA DEL CÓDIGO (DIVIDIDO EN PARTES)
--------------------------------------------------------------------------------
El código está hecho en MicroPython y lo organizamos en 4 partes como si fueran
trabajadores con tareas asignadas:

• Parte 1: El Conector de Wi-Fi (NetworkManager):
  Se encarga de buscar la red de internet en el simulador, conectarse y avisar
  cuando el ESP32 ya tiene acceso a la red.

• Parte 2: El Lector de Sensores (EnvironmentalSensors):
  Lee el sensor DHT22. Como en el simulador no hay perilla física para el sensor
  de gas amoníaco, esta parte calcula valores lógicos y ordenados (entre 15 y
  650 PPM) que suben y bajan suavemente, tal como pasaría en la fábrica.

• Parte 3: El Encargado de Luces y Pantalla (UserInterfaceManager):
  Escribe los textos en la pantalla LCD. Si el gas supera 400 PPM o la temperatura
  pasa de 45°C, prende el LED rojo y apaga el verde. Si todo está normal, deja
  el LED verde prendido.

• Parte 4: El Cerebro Principal (MonomerosController):
  Es el jefe de todo. En un ciclo que nunca se detiene: le pide los datos a los
  sensores, le dice a la pantalla y a los LEDs qué mostrar, revisa si hundiste
  los botones y cada 5 segundos manda el paquete de datos a la API.

--------------------------------------------------------------------------------
4. ¿CÓMO EXPLICARLO? (GUIÓN FÁCIL)
--------------------------------------------------------------------------------
1. ¿Qué hicimos?
   "Profesor, creamos el circuito en Wokwi para monitorear en tiempo real la
   planta de Monómeros usando MicroPython en el ESP32."

2. ¿Qué piezas usamos?
   "Usamos un ESP32, un sensor DHT22 para temperatura y humedad, una pantalla
   LCD con conexión I2C (que solo ocupa los pines 21 y 22), dos LEDs indicadores
   y dos pulsadores."

3. ¿Cómo funciona el sensor de gas?
   "Como el simulador no tiene una perilla interactiva para el sensor de amoníaco,
   seguimos la indicación de la guía: generamos valores lógicos por código entre
   15 y 650 PPM simulando el ambiente de la fábrica."

4. ¿Cómo funcionan las alertas y los botones?
   "Si el gas pasa de 400 PPM o la temperatura pasa de 45°C, se prende el LED
   rojo de emergencia y la pantalla avisa el peligro. Con el botón azul cambiamos
   la pantalla a modo diagnóstico, y con el botón amarillo forzamos el envío de
   datos inmediato a la base de datos."
================================================================================
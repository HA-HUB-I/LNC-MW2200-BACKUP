+================================================
+                                                
+    Vectric machine output configuration file   
+                                                
+================================================
+                                                
+ History                                        
+                                                
+ Who      When       What                         
+ ======== ========== ===========================
+ Tony  V1.0   28/10/2006 Added Arcs to the original postp  
+ Anoop V1.2   03/11/2021 Added H code after Tool change
+ Anoop V1.3   10/11/2021 Modified Strategy for tool change return
+ Anoop V1.4   14/11/2021 Modified post tool change return
+ Anoop V1.5   24/12/2021 X,Y moves removed Tool change, begining
+ Anoop V1.6   03/01/2022 ZH move removed
+ Anoop V1.7   05/01/2022 Tool change, y over travel issue added G90
+ Anoop V1.8   03/02/2022 2nd Tool change, X,Y moving to reference removed.
+ Caleb V1.9   18/09/2022 Changed Start Position
+ Caleb V1.91  18/09/2022 End at work coordinates
+ Caleb V1.92  18/09/2022 Add spindle stop and delay
+ Caleb V2.0   26/12/2024 Add LNC M17 for Cleaning with 2mins
+================================================

POST_NAME = "BEIZA Custom V3(mm) (*.nc)"

FILE_EXTENSION = "nc"

UNITS = "MM"

+------------------------------------------------
+    Line terminating characters                 
+------------------------------------------------

LINE_ENDING = "[13][10]"

+------------------------------------------------
+    Block numbering                             
+------------------------------------------------

LINE_NUMBER_START     = 0
LINE_NUMBER_INCREMENT = 10
LINE_NUMBER_MAXIMUM = 999999

+================================================
+                                                
+    Formating for variables                     
+                                                
+================================================

VAR LINE_NUMBER = [N|A|N|1.0]
VAR SPINDLE_SPEED = [S|A|S|1.0]
VAR FEED_RATE = [F|C|F|1.1]
VAR X_POSITION = [X|C|X|1.3]
VAR Y_POSITION = [Y|C|Y|1.3]
VAR Z_POSITION = [Z|C|Z|1.3]
VAR ARC_CENTRE_I_INC_POSITION = [I|A|I|1.3]
VAR ARC_CENTRE_J_INC_POSITION = [J|A|J|1.3]
VAR X_HOME_POSITION = [XH|A|X|1.3]
VAR Y_HOME_POSITION = [YH|A|Y|1.3]
VAR Z_HOME_POSITION = [ZH|A|Z|1.3]
VAR SAFE_Z_HEIGHT = [SAFEZ|A|Z|1.3]

+================================================
+                                                
+    Block definitions for toolpath output       
+                                                
+================================================

+---------------------------------------------------
+  Commands output at the start of the file
+ G40 → отменя радиусна компенсация на инструмента (G41/G42).
+ G17 → избира равнина XY за интерполация на дъги (по подразбиране, нужно за 2D дървообработка).
+ G80 → отменя активен цикъл за пробиване/кантове (G81…G89).
+ G49 → отменя компенсация на дължина на инструмент (G43/G44).
+---------------------------------------------------

begin HEADER

"[N]G91G28Z0"
"[N]G40G17G80G49"
+ Избери инструмент Tn, след това изпълни M6 (смяна към него)
"[N]T[T]M6"
+ Работи в абсолютен режим (G90) спрямо нулата на детайла, зададена в координатната система G54.
"[N]G90G54"
+"[N]G1[X][Y][Z]"
+ Задай скорост на шпиндела и стартирай шпиндела по часовниковата стрелка
"[N][S]M3"
+"[N]G43[ZH]H[T]"

+---------------------------------------------------
+  Commands output at toolchange
+ add spindle stop
+---------------------------------------------------

begin TOOLCHANGE
+ Връща оста Z в първа референтна точка (home)
"[N]G28G91Z0"
+"[N]G28X0Y0"
"[N]G90"
+ спри шпиндела 
"[N]M5"
+ Пауза секунди 
+ "[N]G4 P8000"
"[N]M6T[T]"
+ Работи в абсолютен режим (G90) спрямо нулата на детайла, зададена в координатната система G54.
"[N]G90G54"
+"[N]G91G28X0Y0"
+"[N]G1[X][Y][Z][S]M3"
"[N][S]M3"
+"[N]G90G43[ZH]H[T]"

+---------------------------------------------------

+ Commands output for Initial rapid move

+---------------------------------------------------

begin INITIAL_RAPID_MOVE

"[N]G0[X][Y]"
"[N]G90G43[Z]H[T]"

+---------------------------------------------------
+  Commands output for rapid moves 
+---------------------------------------------------

begin RAPID_MOVE

"[N]G0[X][Y][Z]"


+---------------------------------------------------
+  Commands output for the first feed rate move
+---------------------------------------------------

begin FIRST_FEED_MOVE

"[N]G1[X][Y][Z][F]"


+---------------------------------------------------
+  Commands output for feed rate moves
+---------------------------------------------------

begin FEED_MOVE

"[N][X][Y][Z]"


+---------------------------------------------------
+  Commands output for the first clockwise arc move
+---------------------------------------------------

begin FIRST_CW_ARC_MOVE

"[N]G02[X][Y][I][J][F]"


+---------------------------------------------------
+  Commands output for clockwise arc  move
+---------------------------------------------------

begin CW_ARC_MOVE

"[N]G02[X][Y][I][J]"


+---------------------------------------------------
+  Commands output for the first counterclockwise arc move
+---------------------------------------------------

begin FIRST_CCW_ARC_MOVE

"[N]G03[X][Y][I][J][F]"


+---------------------------------------------------
+  Commands output for counterclockwise arc  move
+---------------------------------------------------

begin CCW_ARC_MOVE

"[N]G03[X][Y][I][J]"



+---------------------------------------------------
+  Commands output at the end of the file
+ G28 → „return to machine home“ машинния нулев
+---------------------------------------------------

begin FOOTER
+ Връща оста Z в първа референтна точка (home)
"[N]G28G91Z0"
+ отмени компенсации
"[N]G49H0"
+ M5 спри шпиндела , M11 VACUUM PUMP 1 OFF
"[N]M5M11"
+"[N]M17"
+ COUNT OF WORKPIECES
"[N]M30"


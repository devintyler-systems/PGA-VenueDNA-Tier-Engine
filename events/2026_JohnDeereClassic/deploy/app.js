/* PGA VenueDNA — John Deere Classic 2026 */

/* ── Anti-pattern metadata ── */
const AP_META = {
  bomb_and_spray: {
    cls: 'bomb', label: 'Bomb + Spray',
    desc: 'Elite distance with below-field driving accuracy — high tee-box variance at a placement-premium course. Fairway width is moderate; missing it here carries a real short-game penalty.',
    severity: '-1.0 to -2.5',
  },
  wedge_liability: {
    cls: 'wedge', label: 'Wedge Liability',
    desc: 'Below-field wedge proximity inside 150 yd — drag on the highest-weighted scoring trait at Deere Run. This venue bakes in a continual birdie diet; weak wedge play breaks the scoring run.',
    severity: '-2.0 to -5.0',
  },
  poor_birdie_conv: {
    cls: 'birdie', label: 'Poor Birdie Conv',
    desc: 'Low short-putt conversion limits birdie upside at a birdie-fest track. TPC Deere Run returns ~4–5 birdie looks per round; players who cannot convert have no path to contention.',
    severity: '-1.5 to -4.0',
  },
  rough_approach_liab: {
    cls: 'rough', label: 'Rough Approach',
    desc: 'Below-field approach quality from KBG/Fine Fescue rough — a risk multiplier when fairways are missed. Soft conditions amplify this because rough clings and controls spin poorly.',
    severity: '-1.0 to -2.5',
  },
};

const TRAIT_DEFS = [
  { key: 'app_wedge',      label: 'APP Wedge',       desc: 'Approach ≤150 yd (Wedge proximity)',         notation: 'APP_Wedge',     weight: 0.18 },
  { key: 'app_100_150',    label: 'APP 100–150',      desc: 'Mid-iron approach 100–150 yd',               notation: 'APP_100-150',   weight: 0.15 },
  { key: 'putt_short_conv',label: 'Putt Short Conv',  desc: 'Birdie conversion 2–5 ft',                   notation: 'PUTT_BirdieConv',weight:0.14 },
  { key: 'ott_accuracy',   label: 'OTT Accuracy',     desc: 'Positional driving accuracy',                notation: 'OTT_Accuracy',  weight: 0.11 },
  { key: 'putt_lag',       label: 'Putt Lag',         desc: 'Lag putting (3-putt avoidance)',             notation: 'PUTT_Lag',      weight: 0.10 },
  { key: 'par5_scoring',   label: 'Par-5 Scoring',    desc: 'Par-5 scoring leverage',                    notation: 'PAR5_Scoring',  weight: 0.10 },
  { key: 'app_150_200',    label: 'APP 150–200',      desc: 'Long-iron approach 150–200 yd',              notation: 'APP_150-200',   weight: 0.08 },
  { key: 'arg_rough',      label: 'ARG Rough',        desc: 'Rough scrambling (KBG/Fine Fescue)',         notation: 'ARG_Rough',     weight: 0.07 },
  { key: 'ott_distance',   label: 'OTT Distance',     desc: 'Driving distance / power',                  notation: 'OTT_Distance',  weight: 0.04 },
  { key: 'arg_bunker',     label: 'ARG Bunker',       desc: 'Bunker play / sand save rate',              notation: 'ARG_Bunker',    weight: 0.03 },
];

const TRAIT_FIT_DESCS = {
  'PUTT_BirdieConv': 'short-putt conversion (2–5 ft) — elite birdie cash-in rate at a birdie-fest venue',
  'PUTT_Lag':        'lag putting precision — avoids 3-putts, keeps short-putt volume high',
  'APP_Wedge':       'wedge proximity from ≤150 yd — primary scoring lever at TPC Deere Run',
  'APP_100-150':     'mid-iron precision at 100–150 yd — consistent regulation birdie looks',
  'APP_150-200':     'long-iron approach at 150–200 yd — solid from mid-range distances',
  'PAR5_Scoring':    'par-5 scoring leverage — elite conversion on the three par-5 birdie holes',
  'OTT_Accuracy':    'positional driving accuracy — fairway rate on moderate-width fairways',
  'OTT_Distance':    'driving distance / power — limited premium in soft, wet conditions',
  'ARG_Rough':       'rough approach from KBG/Fine Fescue — recovery quality when missing fairways',
  'ARG_Bunker':      'bunker play — greenside sand save conversion rate',
};

const FORM_DATA = {
  'CLARK,WYNDHAM': [3.53,2.28],
  'SCHEFFLER,SCOTTIE': [2.92,-0.27],
  'BURNS,SAM': [2.56,0.94],
  'MCILROY,RORY': [2.43,0.25],
  'THOMAS,JUSTIN': [2.19,1.08],
  'FLEETWOOD,TOMMY': [2.15,0.14],
  'FITZPATRICK,MATT': [2.11,0.05],
  'RAHM,JON': [1.96,-0.18],
  'HATTON,TYRRELL': [1.93,1.04],
  'SPAUN,J.J.': [1.93,0.48],
  'RAI,AARON': [1.84,0.9],
  'CAULEY,BUD': [1.81,1.14],
  'CHACARRA,EUGENIO': [1.78,1.61],
  'NIEMANN,JOAQUIN': [1.77,1.11],
  'COLE,ERIC': [1.76,1.17],
  'FITZPATRICK,ALEX': [1.76,1.24],
  'GRIFFIN,BEN': [1.62,0.21],
  'CANTLAY,PATRICK': [1.58,0.05],
  'GOTTERUP,CHRIS': [1.56,0.11],
  'KIM,SI WOO': [1.56,0.11],
  'REITAN,KRISTOFFER': [1.54,0.64],
  'ROSE,JUSTIN': [1.52,-0.03],
  'HOVLAND,VIKTOR': [1.51,0.11],
  'KITAYAMA,KURT': [1.51,0.28],
  'LOWRY,SHANE': [1.47,0.32],
  'MITCHELL,KEITH': [1.46,0.81],
  'POSTON,J.T.': [1.39,0.71],
  'KOIVUN,JACKSON': [1.38,0.09],
  'MORIKAWA,COLLIN': [1.37,-0.1],
  'ABERG,LUDVIG': [1.34,-0.46],
  'GERARD,RYAN': [1.33,0.44],
  'VINCENT,SCOTT': [1.33,1.04],
  'ENGLISH,HARRIS': [1.32,-0.02],
  'JOHNSON,DUSTIN': [1.31,0.86],
  'MCNEALY,MAVERICK': [1.31,-0.1],
  'POTGIETER,ALDRICH': [1.29,1.22],
  'KIM,TOM': [1.27,0.99],
  'SUBER,JACKSON': [1.25,1.22],
  'HENLEY,RUSSELL': [1.21,-0.55],
  'SCHAUFFELE,XANDER': [1.21,-0.69],
  'REED,PATRICK': [1.18,0.35],
  'SHERWOOD,COLE': [1.16,1.38],
  'BRADLEY,KEEGAN': [1.14,0.22],
  'BAUCHOU,ZACH': [1.13,0.95],
  'BHATIA,AKSHAY': [1.12,-0.15],
  'HARMAN,BRIAN': [1.07,0.42],
  'FOX,RYAN': [1.01,0.57],
  'MACINTYRE,ROBERT': [0.97,-0.44],
  'KANEKO,KOTA': [0.96,1.08],
  'YOUNG,CAMERON': [0.96,-1.08],
  'BURMESTER,DEAN': [0.95,0.7],
  'MATSUYAMA,HIDEKI': [0.94,-0.31],
  'LINDELL,OLIVER': [0.93,0.31],
  'HOJGAARD,NICOLAI': [0.91,-0.18],
  'SMALLEY,ALEX': [0.91,0.28],
  'SNEDEKER,BRANDT': [0.86,0.85],
  'HOWELL III,CHARLES': [0.85,0.48],
  'EICHHORN,HUNTER': [0.85,0.82],
  'GHIM,DOUG': [0.82,0.44],
  'WALLACE,MATT': [0.81,0.37],
  'PEREZ,VICTOR': [0.81,0.66],
  'LEISHMAN,MARC': [0.8,0.51],
  'KIM,MICHAEL': [0.79,0.24],
  'BEZUIDENHOUT,CHRISTIAAN': [0.79,0.09],
  'DECHAMBEAU,BRYSON': [0.78,-0.36],
  'KOHLES,BEN': [0.78,0.75],
  'NOVAK,ANDREW': [0.76,0.46],
  'SMITH,CAMERON': [0.76,0.55],
  'PUIG,DAVID': [0.75,0],
  'THEEGALA,SAHITH': [0.75,0.14],
  'SCOTT,ADAM': [0.74,-0.19],
  'WOODLAND,GARY': [0.74,0.1],
  'HILL,CALUM': [0.72,0.75],
  'NOREN,ALEX': [0.71,-0.5],
  'FINAU,TONY': [0.7,0.69],
  'KNAPP,JAKE': [0.7,-0.82],
  'RYDER,SAM': [0.69,0.84],
  'KOEPKA,BROOKS': [0.68,0.45],
  'COODY,PIERCESON': [0.67,0.24],
  'MCCARTHY,DENNY': [0.67,0.16],
  'LEE,MIN WOO': [0.67,-0.42],
  'GOUVEIA,RICARDO': [0.66,1.5],
  'MEISSNER,MAC': [0.66,-0.06],
  'JENNINGS,WILLIAM': [0.65,1.1],
  'KEEFER,JOHNNY': [0.62,0.5],
  'NORRIS,SHAUN': [0.61,1.62],
  'TAYLOR,NICK': [0.59,-0.23],
  'ECHAVARRIA,NICO': [0.59,0.23],
  'IM,SUNGJAE': [0.58,0.37],
  'AYORA,ANGEL': [0.57,-0.15],
  'SNYMAN,IAN': [0.55,1.27],
  'GREYSERMAN,MAX': [0.55,0.22],
  'SCOTT,SANDY': [0.55,0.85],
  'JAMES,BEN': [0.55,0.23],
  'MOORE,TAYLOR': [0.52,0.54],
  'MORRISON,TOMMY': [0.52,1.01],
  'EWART,A.J.': [0.5,0.68],
  'FISK,STEVEN': [0.5,0.47],
  'VAN ROOYEN,ERIK': [0.48,1.05],
  'BRIDGEMAN,JACOB': [0.45,-0.52],
  'GRILLO,EMILIANO': [0.43,0.39],
  'FERGUSON,EWEN': [0.42,0.47],
  'BERGER,DANIEL': [0.42,0],
  'CARR,BEN': [0.41,1.23],
  'AKINA,KIHEI': [0.41,1.29],
  'SIDES,WILLIAM': [0.41,0.75],
  'KIM,CHAN': [0.4,0.85],
  'BROWN,BLADES': [0.38,0.43],
  'YELLAMARAJU,SUDARSHAN': [0.38,0.19],
  'PONDER,THOMAS': [0.37,0.95],
  'ANCER,ABRAHAM': [0.36,-0.13],
  'NEERGAARD-PETERSEN,RASMUS': [0.35,-0.02],
  'YU,KEVIN': [0.34,0.28],
  'THOMPSON,DAVIS': [0.34,-0.05],
  'PENDRITH,TAYLOR': [0.33,-0.03],
  'KOBORI,KAZUMA': [0.33,0.7],
  'CONNERS,COREY': [0.32,-0.31],
  'HOEY,RICO': [0.31,-0.03],
  'STEINLECHNER,MAXIMILIAN': [0.3,1.16],
  'WIESBERGER,BERND': [0.29,0.79],
  'PUTNAM,ANDREW': [0.29,0.01],
  'WATSON,BUBBA': [0.26,0.35],
  'FOWLER,RICKIE': [0.26,-0.92],
  'GRIFFIN,LANTO': [0.25,0.38],
  'VALIMAKI,SAMI': [0.24,-0.14],
  'BRYANT,DAVIS': [0.23,0.9],
  'ISHIKAWA,RYO': [0.23,0.81],
  'REDMAN,DOC': [0.23,0.6],
  'PEREIRA,COREY': [0.23,0.15],
  'GARCIA,SERGIO': [0.22,0.17],
  'GRACE,BRANDEN': [0.22,-0.52],
  'STOUT,PRESTON': [0.21,0.33],
  'HOSSLER,BEAU': [0.2,0.09],
  'JAKUBCIK,FILIP': [0.2,0.91],
  'SPIETH,JORDAN': [0.2,-0.58],
  'HOGE,TOM': [0.18,0.78],
  'LINDBERG,MIKAEL': [0.17,0.07],
  'SMITH,JORDAN': [0.17,-0.31],
  'YOUNG,CARSON': [0.17,0.53],
  'DOSSEY,COOPER': [0.17,0.19],
  'KIMSEY,NATHAN': [0.16,0.54],
  'DETRY,THOMAS': [0.15,-0.32],
  'HERBERT,LUCAS': [0.15,0.16],
  'HOMA,MAX': [0.14,-0.35],
  'RITCHIE,JC': [0.13,0.26],
  'THORBJORNSEN,MICHAEL': [0.12,-0.59],
  'COUSSAUD,UGO': [0.12,0.3],
  'HALL,HARRY': [0.11,-0.87],
  'SKINNS,DAVID': [0.1,0.45],
  'JOHNSON,MICHAEL': [0.09,0.24],
  'FISHBURN,PATRICK': [0.08,0.16],
  'MCCARTY,MATT': [0.08,-0.65],
  'DE LEO,GREGORIO': [0.08,0.68],
  'OLESEN,JACOB SKOV': [0.08,0.14],
  'STEVENS,SAM': [0.07,-0.4],
  'HUBBARD,MARK': [0.07,0.3],
  'SMOTHERMAN,AUSTIN': [0.06,0.05],
  'MAAS,CHRISTIAAN': [0.05,0.09],
  'KUCHAR,MATT': [0.05,-0.14],
  'ORTIZ,ALVARO': [0.05,0.77],
  'MIGLIOZZI,GUIDO': [0.04,0.79],
  'GARNETT,BRICE': [0.03,0.67],
  'MOUW,WILLIAM': [0.01,-0.33],
  'PEPPERELL,EDDIE': [0.01,0.35],
  'TAYLOR,BEN': [0,0.49],
  'GOOCH,TALOR': [0,-0.16],
  'JOHNSON,ZACH': [-0.01,0.13],
  'CASTILLO,RICKY': [-0.01,-0.27],
  'DAY,JASON': [-0.02,-0.63],
  'MCGREEVY,MAX': [-0.03,-0.38],
  'HILLIER,DANIEL': [-0.04,-0.58],
  'HISATSUNE,RYO': [-0.04,-0.16],
  'KIM,S.H.': [-0.04,0.14],
  'BRENNAN,MICHAEL': [-0.05,-0.44],
  'BLAIR,ZAC': [-0.05,-0.04],
  'STEELMAN,ROSS': [-0.05,0.76],
  'NAKAJIMA,KEITA': [-0.05,0.09],
  'WARING,PAUL': [-0.06,0.6],
  'OLESEN,THORBJORN': [-0.06,-0.44],
  'PAVON,MATTHIEU': [-0.06,0.18],
  'DOU,ZECHENG': [-0.07,-0.12],
  'MENANTE,DYLAN': [-0.08,0.56],
  'LUNDIN,JACK': [-0.08,1.01],
  'ERENO PEREZ,PABLO': [-0.08,0.75],
  'DEAN,JOE': [-0.09,0.84],
  'STEELE,BRENDAN': [-0.1,0.53],
  'VARNER III,HAROLD': [-0.1,0.28],
  'HORSCHEL,BILLY': [-0.1,0.04],
  'REAVIE,CHEZ': [-0.11,0.79],
  'SHORE,DAVIS': [-0.11,0.39],
  'HIGGO,GARRICK': [-0.11,-0.18],
  'NOH,S.Y.': [-0.12,0.26],
  'RAVETTO,DAVID': [-0.12,0.7],
  'HUGHES,MACKENZIE': [-0.12,-0.09],
  'ARMITAGE,MARCUS': [-0.12,-0.06],
  'GUERRIER,JULIEN': [-0.12,-0.04],
  'ROZNER,ANTOINE': [-0.15,0.04],
  'NORGAARD,NIKLAS': [-0.16,0.61],
  'CROWE,TRACE': [-0.17,0.23],
  'AN,BYEONG HUN': [-0.17,0.1],
  'SONG,YOUNGHAN': [-0.18,0.5],
  'DAFFUE,MJ': [-0.18,0.93],
  'PAK,JOHN': [-0.18,0.32],
  'HITT,AUSTIN': [-0.19,0.54],
  'ECKROAT,AUSTIN': [-0.2,-0.26],
  'HARRIS,FRANKIE': [-0.21,0.77],
  'POWER,SEAMUS': [-0.21,-0.23],
  'MCKIBBIN,TOM': [-0.21,-0.6],
  'COUVRA,MARTIN': [-0.22,0.15],
  'COWAN,RYDER': [-0.23,0.68],
  'JANG,YUBIN': [-0.24,0.77],
  'WHALEY,VINCE': [-0.24,-0.38],
  'CLANTON,LUKE': [-0.24,0.55],
  'PARRY,JOHN': [-0.25,-0.63],
  'VAILLANT,TOM': [-0.25,0.01],
  'MCALLISTER,LOGAN': [-0.26,0.69],
  'SUMMY,JASE': [-0.26,0.55],
  'KAYMER,MARTIN': [-0.27,0.45],
  'CANTER,LAURIE': [-0.27,0.12],
  'KANAYA,TAKUMI': [-0.27,-0.32],
  'DOCHERTY,ALISTAIR': [-0.28,0.33],
  'JARVIS,CASEY': [-0.29,-0.32],
  'SCHMID,MATTI': [-0.29,-0.35],
  'HADWIN,ADAM': [-0.29,0.34],
  'POULTER,IAN': [-0.3,0.59],
  'KIRK,CHRIS': [-0.3,-0.59],
  'VAN DRIEL,DARIUS': [-0.31,0.43],
  'BUCKLEY,HAYDEN': [-0.31,0.36],
  'WANG,JEUNGHUN': [-0.31,0.63],
  'DUMONT DE CHASSART,ADRIEN': [-0.33,-0.45],
  'WINTHER,JEFF': [-0.33,0.39],
  'POTTER,LUKE': [-0.34,0.79],
  'GUILLAMOUNDEGUY,OIHAN': [-0.34,0.21],
  'SUH,JUSTIN': [-0.34,0.64],
  'SVENSSON,JESPER': [-0.34,-0.14],
  'PETERSON,PAUL': [-0.35,0.07],
  'DEL REY,ALEJANDRO': [-0.35,0.12],
  'STANGER,JIMMY': [-0.35,0.08],
  'OOSTHUIZEN,LOUIS': [-0.35,-0.25],
  'DUNLAP,NICK': [-0.35,0.47],
  'LI,HAOTONG': [-0.35,-0.49],
  'PREMLALL,YURAV': [-0.35,1.26],
  'NAGANO,RYUTARO': [-0.36,0.58],
  'STREELMAN,KEVIN': [-0.36,0.53],
  'CAMPILLO,JORGE': [-0.36,-0.26],
  'APHIBARNRAT,KIRADECH': [-0.36,0.54],
  'VILIPS,KARL': [-0.37,0.09],
  'ZHOU,YANHAN': [-0.37,0.09],
  'SCHAPER,JAYDEN': [-0.37,-1.03],
  'FIORONI,CADEN': [-0.37,0.76],
  'GILLIGAN,IAN': [-0.39,0.14],
  'SVENSSON,ADAM': [-0.39,0.07],
  'VAN DER MERWE,GRAHAM': [-0.4,1.22],
  'SIMPSON,WEBB': [-0.4,-0.23],
  'GOMEZ,FABIAN': [-0.4,0.4],
  'BUTLER,JOHN MARSHALL': [-0.4,0.87],
  'MUNOZ,SEBASTIAN': [-0.4,-0.71],
  'YONEZAWA,REN': [-0.4,0.27],
  'VANARRAGON,CALEB': [-0.41,-0.18],
  'FIGUEIREDO,PEDRO': [-0.42,0.88],
  'BRADBURY,DAN': [-0.42,-0.3],
  'JORDAN,MATTHEW': [-0.43,0.03],
  'SMYLIE,ELVIS': [-0.43,-0.32],
  'WILLIAMS,MASON': [-0.43,0.47],
  'BARRON,HAYDN': [-0.44,0.43],
  'KANG,JEFFREY': [-0.45,0.38],
  'KATSUMATA,RYO': [-0.45,0.61],
  'LIPSKY,DAVID': [-0.46,-0.52],
  'VEGAS,JHONATTAN': [-0.46,-0.01],
  'KHO,TAICHI': [-0.47,0.68],
  'MEISSNER,MITCHELL': [-0.47,0.34],
  'HODGES,LEE': [-0.47,-0.41],
  'MOLINARI,FRANCESCO': [-0.47,-0.11],
  'RUSSELL,MILES': [-0.48,-0.17],
  'JUNG,CHANMIN': [-0.48,1.12],
  'EGE,MATS': [-0.48,1],
  'VAN TONDER,DANIEL': [-0.48,0.53],
  'FRITTELLI,DYLAN': [-0.49,0.43],
  'CABRERA BELLO,RAFA': [-0.5,-0.11],
  'NYHOLM,PONTUS': [-0.51,0.16],
  'RODGERS,PATRICK': [-0.51,-0.61],
  'HOSONO,YUSAKU': [-0.51,0.33],
  'PHILLIPS,CHANDLER': [-0.51,-0.07],
  'DA COSTA RODRIGUES,DANIEL': [-0.51,0.12],
  'BOLTON,BEN': [-0.52,0.41],
  'HIDALGO PORTILLO,ANGEL': [-0.52,0.71],
  'SHEILS DONEGAN,NIALL': [-0.52,0.76],
  'RAMEY,CHAD': [-0.52,-0.58],
  'WU,ASHUN': [-0.52,0.42],
  'LEVY,ALEXANDER': [-0.53,0.33],
  'CHANG,PAUL': [-0.53,0.61],
  'JUNG,HANMIL': [-0.54,1.43],
  'FUJIMOTO,YOSHINORI': [-0.54,0.88],
  'KINHULT,MARCUS': [-0.54,0.43],
  'PRINSLOO,JACO': [-0.55,0.39],
  'BERGSTROM,ALBIN': [-0.55,0.75],
  'BLANCHET,CHANDLER': [-0.55,-0.72],
  'SPRINGER,HAYDEN': [-0.55,-0.22],
  'IDERIHA,TAICHIRO': [-0.56,1.14],
  'SHIPLEY,NEAL': [-0.57,-0.31],
  'SATO,TAIHEI': [-0.57,0.44],
  'HACK,JHARED': [-0.57,0.21],
  'YUAN,CARL': [-0.57,0.44],
  'PENGE,MARCO': [-0.58,-1.07],
  'MANASSERO,MATTEO': [-0.58,0.14],
  'PENG,BO': [-0.6,1.51],
  'SADDIER,ADRIEN': [-0.6,-0.45],
  'HALVORSEN,ANDREAS': [-0.61,0.04],
  'ATKINS,MATT': [-0.61,0.27],
  'BROWN,DAN': [-0.61,-0.8],
  'ELVIRA MIJARES,IGNACIO': [-0.61,0.06],
  'LAHIRI,ANIRBAN': [-0.62,0.03],
  'SAVOIE,JOEY': [-0.62,1.2],
  'VRZICH,JOEY': [-0.62,0.67],
  'THOMAS,RAYHAN': [-0.63,0.61],
  'WILLETT,DANNY': [-0.64,0.61],
  'TRUSLOW,AUSTEN': [-0.64,0.06],
  'LANGASQUE,ROMAIN': [-0.65,0.03],
  'SOLOMON,JACOB': [-0.66,0.89],
  'HIGGS,HARRY': [-0.66,0.2],
  'WIEDEMEYER,TIM': [-0.66,0.34],
  'LAGERGREN,JOAKIM': [-0.66,-0.21],
  'BAE,YONGJUN': [-0.67,0.36],
  'LEBIODA,HANK': [-0.68,-0.21],
  'TETAK,TADEÁŠ': [-0.69,1.33],
  'JOHANNESSEN,KRISTIAN K.': [-0.69,0.2],
  'SILVERMAN,BEN': [-0.69,-0.1],
  'KINOSHITA,RYOSUKE': [-0.7,-0.05],
  'KIM,ANTHONY': [-0.7,0.15],
  'VENTURA,KRIS': [-0.7,-0.77],
  'WESTMORELAND,KYLE': [-0.71,0.71],
  'ORTIZ,CARLOS': [-0.71,-0.65],
  'MAZZOLI,STEFANO': [-0.71,0.39],
  'FLAVIN,PATRICK': [-0.71,0.68],
  'CANNON,WILL': [-0.71,0.13],
  'DOUGHERTY,KEVIN': [-0.72,0.13],
  'FRANCOEUR,CHRIS': [-0.72,0.21],
  'SCRIVENER,JASON': [-0.73,0.03],
  'HARRINGTON,PADRAIG': [-0.73,0.62],
  'GOODMAN,DREW': [-0.73,0.54],
  'EASTERBROOK,SAM': [-0.73,1.34],
  'NABETANI,TAICHI': [-0.73,1],
  'BALLESTER,JOSE LUIS': [-0.73,-0.83],
  'LEE,SANG-HEE': [-0.73,0.78],
  'WOLCOTT,HUNTER': [-0.74,1.13],
  'TRACE,TRAVIS': [-0.74,0.13],
  'ELVIRA,MANUEL': [-0.75,-0.11],
  'ADAM,CAMERON': [-0.75,0.43],
  'BROWN,HAMISH': [-0.75,0.41],
  'HUMPHREY,THEO': [-0.75,0.6],
  'GALLETTI,NICOLO': [-0.75,-0.38],
  'SCHOTT,FREDDY': [-0.76,0.23],
  'ANDERSEN,MASON': [-0.76,-0.07],
  'TANKERSLEY,CAMERON': [-0.76,0.55],
  'KATSURAGAWA,YUTO': [-0.76,0.31],
  'MOLDOVAN,MAXWELL': [-0.76,0.48],
  'LAMB,RICK': [-0.76,0.14],
  'ALBERTSE,LOUIS': [-0.77,0.83],
  'JAEGER,STEPHAN': [-0.77,-0.61],
  'RAMSAY,RICHIE': [-0.77,0.07],
  'KOZUMA,JINICHIRO': [-0.77,0.43],
  'CATLIN,JOHN': [-0.77,0.5],
  'TRINGALE,CAMERON': [-0.77,-0.34],
  'DING,WENYI': [-0.77,-0.5],
  'MALNATI,PETER': [-0.78,-0.13],
  'ROBINSON THOMPSON,BRANDON': [-0.78,-0.27],
  'DOYLE,DREW': [-0.78,1.12],
  'LEE,HYUNGJOON': [-0.79,1.18],
  'ROY,KEVIN': [-0.79,-0.78],
  'CRISTONI,MATTEO': [-0.79,1.05],
  'GOOSEN,RETIEF': [-0.79,0.63],
  'SIMPSON,SAMUEL': [-0.8,0.82],
  'DU PLESSIS,HENNIE': [-0.8,-0.96],
  'LEDESMA,NELSON': [-0.8,0.61],
  'CHOI,SAM': [-0.81,0.75],
  'NICHOLAS,JAMES': [-0.82,0.03],
  'NEWCOMB,PATRICK': [-0.82,0.03],
  'DANTORP,JENS': [-0.83,0.25],
  'PHILLIPS,TRENT': [-0.83,-0.48],
  'BRAMLETT,JOSEPH': [-0.84,-0.16],
  'BROWN,BARCLAY': [-0.85,1.21],
  'GOFF,ALEX': [-0.85,0.41],
  'WALLIN,ADAM': [-0.86,0.28],
  'IKEMURA,TOMOYO': [-0.86,0.32],
  'GIBOUDOT,MAXENCE': [-0.87,0.87],
  'SUGIURA,YUTA': [-0.87,0.07],
  'SOUTHGATE,MATTHEW': [-0.88,1.09],
  'SHEEHAN,PATRICK': [-0.88,0.68],
  'SODERBERG,SEBASTIAN': [-0.89,0.17],
  'LEWIS,RILEY': [-0.89,0.01],
  'COTTAM,KYLE': [-0.89,0.06],
  'SIMONSEN,MARTIN': [-0.89,0.77],
  'SLOAN,ROGER': [-0.89,-0.1],
  'CLEMENTS,TODD': [-0.89,-0.52],
  'ENNIS,WHEATON': [-0.9,0.68],
  'MUN,DOYEOB': [-0.9,-0.07],
  'SURRATT,CALEB': [-0.91,-0.62],
  'STONE,BRANDON': [-0.91,-0.15],
  'LEE,SOOMIN': [-0.91,0.72],
  'FISCHER,ZACK': [-0.93,0.36],
  'STRAKA,SEPP': [-0.93,-1.49],
  'ELS,ERNIE': [-0.93,0.11],
  'CARD III,JAY': [-0.94,0.02],
  'PETTIT,TURK': [-0.94,0.35],
  'LAMB,DAVIS': [-0.94,-0.36],
  'SCHNEIDER,MARCEL': [-0.94,-0.23],
  'GLOVER,LUCAS': [-0.94,-0.7],
  'HEND,SCOTT': [-0.94,0.74],
  'CELIA,RICARDO': [-0.94,0.61],
  'ROMANO,ANDREA': [-0.95,0.88],
  'PIETERS,THOMAS': [-0.95,-1.02],
  'GRINBERG,LEV': [-0.95,0.75],
  'CAMPBELL,BRIAN': [-0.95,-0.04],
  'LAPORTA,FRANCESCO': [-0.96,-0.77],
  'BAKER,ELIOT': [-0.96,0.24],
  'SEMIKAWA,TAIGA': [-0.96,-0.58],
  'TURNER,JACK': [-0.96,0.1],
  'ENEFER,WILL': [-0.97,0.43],
  'FISHER,ROSS': [-0.97,0.43],
  'HIRATA,KENSEI': [-0.97,-0.02],
  'FORREST,GRANT': [-0.98,-0.75],
  'SCHWARTZEL,CHARL': [-0.98,-0.57],
  'MAEDA,KOSHIRO': [-0.98,0.64],
  'CHOI,SEUNGBIN': [-0.98,0.07],
  'HOSHINO,RIKUYA': [-0.99,0.04],
  'KOZAN,ANDREW': [-0.99,0.36],
  'GABRELCIK,NICK': [-0.99,-0.02],
  'GARCIA,JORGE': [-1,0.69],
  'LEWTON,STEVE': [-1,0.74],
  'SMYTH,TRAV': [-1,-0.29],
  'DUNCAN,TYLER': [-1,0.04],
  'STERNE,RICHARD': [-1.01,-0.46],
  'MERRITT,TROY': [-1.01,0.21],
  'LACROIX,FREDERIC': [-1.01,-0.39],
  'HALE JR,BLAINE': [-1.02,0.57],
  'WILKES,TYLER': [-1.04,0.63],
  'ROZO,MARCELO': [-1.04,0.19],
  'NESBITT,DREW': [-1.04,0.27],
  'SCHMIDT,BEN': [-1.05,-0.35],
  'PEACOCK,JAKE': [-1.05,0.67],
  'BLAND,RICHARD': [-1.05,-0.4],
  'KOKRAK,JASON': [-1.05,-0.5],
  'SULLIVAN,ANDY': [-1.07,-0.83],
  'WALKER,EUAN': [-1.07,0.24],
  'TOSTI,ALEJANDRO': [-1.07,0.5],
  'CREEL,JOSHUA': [-1.08,0.7],
  'SUMMERHAYS,PRESTON': [-1.08,0.74],
  'KOCHER,DAVID': [-1.09,0.42],
  'HARDY,NICK': [-1.1,-0.08],
  'CANTERO GUTIERREZ,IVAN': [-1.11,0.33],
  'QUAYLE,ANTHONY': [-1.11,-0.02],
  'BLAUM,RYAN': [-1.11,0.32],
  'MERONK,ADRIAN': [-1.12,-0.29],
  'CHATFIELD,DAVIS': [-1.12,-0.51],
  'VILLEGAS,CAMILO': [-1.13,-0.1],
  'KNOWLES,PHILIP': [-1.17,0.52],
  'LEE,DANNY': [-1.17,0.56],
  'PARATORE,RENATO': [-1.17,0.28],
  'DICKSON,TAYLOR': [-1.17,0.28],
  'KORTE,CHRIS': [-1.18,-0.07],
  'KRUYSWIJK,JACQUES': [-1.18,-0.41],
  'WU,BRANDON': [-1.19,0.54],
  'CELLI,FILIPPO': [-1.19,0.19],
  'UIHLEIN,PETER': [-1.19,-0.57],
  'BALDWIN,MATTHEW': [-1.19,0.49],
  'BJERREGAARD,LUCAS': [-1.2,0.09],
  'MORY,FELIX': [-1.2,0.41],
  'HRUBY,PETR': [-1.21,-0.25],
  'SHARMA,SHUBHANKAR': [-1.23,0.44],
  'BLOMME,ADAM': [-1.23,0.64],
  'SHELTON,ROBBY': [-1.23,-0.16],
  'HAMMER,COLE': [-1.24,-0.61],
  'OTAEGUI,ADRIAN': [-1.24,-0.41],
  'PAUL,JEREMY': [-1.24,-0.12],
  'LAWRENCE,THRISTON': [-1.24,-0.92],
  'WESTWOOD,LEE': [-1.25,-0.6],
  'XIONG,NORMAN': [-1.25,0.44],
  'KNOX,RUSSELL': [-1.25,-0.13],
  'MASAVEU,LUIS': [-1.26,0],
  'HITCHNER,DEREK': [-1.26,-0.26],
  'SCHENK,ADAM': [-1.29,-0.14],
  'LEMKE,NIKLAS': [-1.3,-0.22],
  'WILLIAMS,ROBIN': [-1.31,0.42],
  'LEE,RICHARD': [-1.32,-0.96],
  'BAIRSTOW,SAM': [-1.32,-0.22],
  'LAMPRECHT,CHRISTO': [-1.34,-0.53],
  'HOLLICK,MICHAEL': [-1.34,-0.11],
  'LEACH,TYLER': [-1.35,0.29],
  'GANDON,JEREMY': [-1.35,-0.66],
  'YOUNG,DANIEL': [-1.36,-0.41],
  'GUTSCHEWSKI,LUKE': [-1.37,-0.46],
  'LA SASSO,MICHAEL': [-1.37,0.64],
  'PAUL,YANNIK': [-1.38,0.48],
  'NORLANDER,HENRIK': [-1.38,-0.28],
  'WU,DYLAN': [-1.38,-0.9],
  'HARKINS,BRANDON': [-1.39,0.62],
  'SARGENT,GORDON': [-1.39,-0.17],
  'MORRISON,JAMES': [-1.4,0.09],
  'CROCKER,SEAN': [-1.4,-0.24],
  'SCHMIDT,THOMAS': [-1.4,0.39],
  'LAW,DAVID': [-1.41,-0.5],
  'DAHMEN,JOEL': [-1.41,-1.06],
  'BOTHA,BAREND': [-1.41,-0.82],
  'LAIRD,MARTIN': [-1.41,-0.36],
  'LIST,LUKE': [-1.41,-0.12],
  'TEATER,JOSH': [-1.42,0.45],
  'LOMBARD,ZANDER': [-1.42,-0.31],
  'GOODWIN,NOAH': [-1.42,-0.74],
  'LEE,JUNGHWAN': [-1.43,-0.31],
  'KAEWKANJANA,SADOM': [-1.44,-0.64],
  'CONE,TREVOR': [-1.44,-0.93],
  'VEERMAN,JOHANNES': [-1.44,-0.3],
  'DEL SOLAR,CRISTOBAL': [-1.45,0.02],
  'TOWNSEND,HUGO': [-1.46,-0.4],
  'WALKER,DANNY': [-1.5,-0.37],
  'NAIDOO,DYLAN': [-1.5,0.63],
  'GORDON,WILL': [-1.51,-0.2],
  'JONSSON,TOBIAS': [-1.51,-0.23],
  'VON DELLINGSHAUSEN,NICOLAI': [-1.51,-0.38],
  'VOOIS,RYAN': [-1.53,-0.12],
  'CHANDLER,WILL': [-1.53,-0.09],
  'LUITEN,JOOST': [-1.54,-1.13],
  'GARCIA RODRIGUEZ,SEBASTIAN': [-1.55,-0.21],
  'LOWER,JUSTIN': [-1.55,-0.74],
  'SURI,JULIAN': [-1.56,-0.67],
  'VAN PARIS,JACKSON': [-1.56,-0.56],
  'ARNAUS,ADRI': [-1.57,-0.08],
  'BURNETT,RYAN': [-1.57,0],
  'DUNCAN,AUSTIN': [-1.58,0.22],
  'WHITNEY,TOM': [-1.6,-0.43],
  'CHAMP,CAMERON': [-1.6,-0.83],
  'RILEY,DAVIS': [-1.61,-0.33],
  'VANDERLAAN,JOHN': [-1.61,-1.06],
  'TABUENA,MIGUEL': [-1.62,-0.31],
  'MARZILIO,VICENTE': [-1.65,0.31],
  'NESMITH,MATT': [-1.69,-0.03],
  'GUMBERG,JORDAN': [-1.69,-0.08],
  'RIEDEL,MATTHEW': [-1.7,-0.15],
  'ZANOTTI,FABRIZIO': [-1.7,-0.04],
  'REPETTO TAYLOR,ROCCO PAOLO': [-1.7,-0.44],
  'GIBSON,RHEIN': [-1.71,-0.21],
  'HOLT,IAN': [-1.73,-1.37],
  'BYRD,JONATHAN': [-1.75,-0.98],
  'GUTHRIE,LUKE': [-1.75,-0.29],
  'FEAGLES,MICHAEL': [-1.76,-0.32],
  'BIONDI,FRED': [-1.77,-0.25],
  'ROSENMUELLER,THOMAS': [-1.78,-1.19],
  'FOOS,DOMINIC': [-1.78,-0.09],
  'MAICHON,PHICHAKSN': [-1.79,-0.22],
  'FERNANDEZ VALDES,JORGE': [-1.81,-1.2],
  'VIDAL,QUIM': [-1.82,0.21],
  'LEWIS,BRYCE': [-1.83,-0.34],
  'MCDOWELL,GRAEME': [-1.83,-0.71],
  'INFANTI,NICK': [-1.83,0.29],
  'STEGMAIER,BRETT': [-1.84,-0.16],
  'VAN HORNE,ASHTON': [-1.85,-0.51],
  'HIGHSMITH,JOE': [-1.85,-0.36],
  'ANDERSON,MATTHEW': [-1.86,-0.34],
  'SARGENT,BILLY TOM': [-1.86,-0.41],
  'CAPPELEN,SEBASTIAN': [-1.87,-0.11],
  'LEE,K.H.': [-1.87,0.42],
  'BUCHANAN,JACK': [-1.88,-0.05],
  'GIRRBACH,JOEL': [-1.89,-1],
  'OPPENHEIM,ROB': [-1.9,-0.06],
  'CAMPBELL,BEN': [-1.92,-0.51],
  'HELLGREN,BJORN': [-1.94,-0.41],
  'WHITE,BRETT': [-1.96,-0.57],
  'THORNBERRY,BRADEN': [-1.96,-0.23],
  'WOLFF,MATTHEW': [-2,-0.66],
  'NIMMER,BRYSON': [-2,-0.23],
  'HOFFMAN,CHARLEY': [-2,0.17],
  'BUCHANAN,JACKSON': [-2.01,-0.79],
  'SANDHU,YUVRAJ SINGH': [-2.02,-0.33],
  'CHARMASSON,CLEMENT': [-2.04,-0.39],
  'PEAKE,RYAN': [-2.04,0.03],
  'MONTGOMERY,TAYLOR': [-2.04,-1.64],
  'STRYDOM,OCKIE': [-2.05,0.5],
  'NUNEZ,AUGUSTO': [-2.06,-0.21],
  'SENIOR,JACK': [-2.07,-0.78],
  'HORSFIELD,SAM': [-2.1,0.05],
  'MARTIN,BEN': [-2.11,-0.95],
  'TARREN,CALLUM': [-2.15,-0.44],
  'MACDONALD,STUART': [-2.18,-1.16],
  'LARRAZABAL,PABLO': [-2.21,-0.42],
  'SEWELL,CHAD': [-2.22,-0.64],
  'BARJON,PAUL': [-2.22,0.55],
  'MICHELUZZI,DAVID': [-2.22,-0.5],
  'JAMIESON,SCOTT': [-2.22,-0.83],
  'CAMPOS,RAFAEL': [-2.26,-0.44],
  'GREY,J.J.': [-2.28,-0.09],
  'MEISEL,MARSHALL': [-2.28,-0.64],
  'SIEM,MARCEL': [-2.31,-0.64],
  'BREHM,RYAN': [-2.32,-0.25],
  'KIM,MINKYU': [-2.32,-0.31],
  'ASAJI,YOSUKE': [-2.34,-0.67],
  'MOLINARI,EDOARDO': [-2.39,-0.46],
  'MAGUIRE,JACK': [-2.41,-0.39],
  'KO,JEONG WEON': [-2.41,-0.06],
  'KIEFFER,MAX': [-2.41,-0.72],
  'SUMMERHAYS,DANIEL': [-2.42,-0.87],
  'WEILER,JOE': [-2.45,-0.8],
  'BROOMHEAD,JONOTHAN': [-2.47,-0.35],
  'OVERTON,JEFF': [-2.5,-0.38],
  'DAVIS,CAM': [-2.51,-0.77],
  'LOGAN,HUNTER': [-2.51,-0.06],
  'JOHNSTON,RYGGS': [-2.51,-0.4],
  'ALEXANDER,TYSON': [-2.56,-0.43],
  'KIZZIRE,PATTON': [-2.56,-1.5],
  'SYME,CONNOR': [-2.59,-1.02],
  'SULLIVAN,RYAN': [-2.61,-0.07],
  'HASTINGS,JUSTIN': [-2.62,-1.04],
  'FOLLET-SMITH,BENJAMIN': [-2.64,-0.74],
  'BACHA,CARSON': [-2.65,-1.39],
  'DEBOVE,QUENTIN': [-2.74,-0.8],
  'FURR,WILSON': [-2.76,-1.5],
  'KOLLE,FINN': [-2.78,0.03],
  'VOGELSONG,ALEX': [-2.85,-0.18],
  'BERRY,BRANDON': [-2.94,-1.03],
  'GALLEGOS,ANDRES': [-2.97,-0.27],
  'LEVIN,SPENCER': [-3.28,-1.05],
  'WINSTEAD,TREY': [-3.34,-1.33],
  'SONG,JAMES': [-3.36,0.38],
  'YULE,JACK': [-3.38,-0.64],
  'HIGGINS,ROBBIE': [-3.5,-0.86],
  'MCKINNEY,CONNOR': [-3.78,-1.44],
  'TOOROP,MIKE': [-3.8,-1.08],
  'STEWART,DILLON': [-4.21,-2.13],
  'BERRY,JOSHUA': [-4.45,-1.9],
  'MATTHEWS,BRANDON': [-4.57,-0.04],
};

/* ── Global state ── */
let PAYLOAD      = null;
let allPlayers   = [];
let searchQuery  = '';
let activeTier   = 'all';
let sortCol      = 'rank';
let sortDir      = 1;        // 1 = asc, -1 = desc
let filterFlagged = false;
let filterDebut  = false;
let BRIEFS_MAP = {};  /* player_name → brief object */
let filterFormPositive = false;
let filterFormNegative = false;
let filterFormHot     = false;
let filterFormCold    = false;
let filterVtsMin      = null;
let filterWinMin      = null;
let filterSgMin       = null;

const DATA_PATH = 'data/event_payload.json';

/* Normalize player name to match FORM_DATA keys: "Last, First" → "LAST,FIRST" */
function formKey(name) {
  return (name || '').toUpperCase().replace(/,\s+/, ',').trim();
}

function computeFormStats() {
  const vals = [];
  for (const p of allPlayers) {
    const fd = FORM_DATA[formKey(p.player_name)];
    if (fd) vals.push(0.6 * fd[0] + 0.4 * fd[1]);
  }
  if (!vals.length) return { mean: 0, sd: 1 };
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const sd   = Math.sqrt(vals.map(v => (v - mean) ** 2).reduce((a, b) => a + b, 0) / vals.length);
  return { mean, sd: Math.max(sd, 0.01) };
}

function applyFormAdjustments() {
  const { mean, sd } = computeFormStats();
  for (const p of allPlayers) {
    p.vts_original = Number(p.vts_final);
    const fd = FORM_DATA[formKey(p.player_name)];
    if (!fd) {
      p.form_sg_putt = null;
      p.form_sg_arg  = null;
      p.form_raw     = null;
      p.form_adj     = 0;
      p.form_missing = true;
    } else {
      p.form_sg_putt = fd[0];
      p.form_sg_arg  = fd[1];
      const formRaw  = 0.6 * fd[0] + 0.4 * fd[1];
      p.form_raw     = formRaw;
      const z        = (formRaw - mean) / sd;
      p.form_adj     = Math.max(-4.0, Math.min(4.0, z * 1.5));
      p.form_missing = false;
    }
    p.vts_final = (Math.max(0, Math.min(100, p.vts_original + p.form_adj))).toFixed(1);
  }
  allPlayers.sort((a, b) => Number(b.vts_final) - Number(a.vts_final));
  allPlayers.forEach((p, i) => { p.rank = i + 1; });
}

/* ════════════════════════════════════════════
   BOOT
════════════════════════════════════════════ */
async function init() {
  try {
    PAYLOAD = await fetch(DATA_PATH).then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });
  } catch (e) {
    document.body.innerHTML =
      `<div style="padding:2rem;color:#fca5a5;font-family:monospace">
        Failed to load payload: ${e.message}<br>
        Expected: ${DATA_PATH}
      </div>`;
    return;
  }

  try {
    const briefs = await fetch('data/player_briefs.json').then(r => r.json());
    /* Flatten all tiers into map keyed by player_name */
    for (const key of Object.keys(briefs)) {
      if (Array.isArray(briefs[key])) {
        for (const b of briefs[key]) {
          if (b.player_name) BRIEFS_MAP[b.player_name] = b;
        }
      }
    }
  } catch (_) { /* briefs are optional enhancements */ }

  /* Build flat player list from tier objects (tiers are already rank-sorted) */
  allPlayers = [];
  for (let t = 1; t <= 5; t++) {
    for (const p of (PAYLOAD.tiers[`tier_${t}`] || [])) {
      p.flag_count = p.anti_pattern_flags
        ? p.anti_pattern_flags.split(';').filter(Boolean).length
        : 0;
      allPlayers.push(p);
    }
  }
  allPlayers.sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999));
  applyFormAdjustments();

  /* Tighten tier thresholds and sharpen win% curve before rendering */
  recomputeTiers();
  recomputeWinPct();

  renderHeader();
  renderInfoStrip();
  renderWinnerSection();
  renderDecisionBoard();
  renderTraitWeights();
  renderAPPanel();
  renderTierSections();
  renderAuditFooter();
  renderSiteFooter();

  wireSearch();
  wireTierTabs();
  wireSort();
  wireToggles();
  wireModal();
  wireGlossary();

  applyAndRender();
}

/* ════════════════════════════════════════════
   HELPERS
════════════════════════════════════════════ */
function fmtName(raw) {
  if (!raw) return '';
  const parts = raw.split(',').map(s => s.trim());
  return parts.length > 1 ? `${parts[1]} ${parts[0]}` : raw;
}

function kv(label, val) {
  const display = (val === null || val === undefined || val === '') ? '—' : val;
  return `<div class="kv"><span class="k">${label}</span><span class="v">${display}</span></div>`;
}

function apChip(flag) {
  const m = AP_META[flag];
  if (!m) return '';
  return `<span class="ap-chip ${m.cls}" title="${m.label}: ${m.desc.split('.')[0]}">${m.label}</span>`;
}

function debutChip(p) {
  if (!p.debut_flag) return '';
  const cls = (p.debut_class || '').toUpperCase() === 'A' ? 'debut-a' : 'debut-b';
  return `<span class="debut-chip ${cls}" title="Debut at TPC Deere Run — Class ${p.debut_class}">DEBUT-${p.debut_class || '?'}</span>`;
}

function tierBadge(tier, label) {
  return `<span class="tier-badge t${tier}">${label || `T${tier}`}</span>`;
}

function vfdDisplay(vfd, showIcon = false) {
  if (vfd === null || vfd === undefined) return '<span style="color:var(--muted)">—</span>';
  const fav  = vfd <= 0;
  const cls  = fav ? 'vfd-neg' : 'vfd-pos';
  const icon = showIcon ? (fav ? ' ★' : ' ▲') : '';
  const tip  = fav
    ? `Fit Edge +${Math.abs(Number(vfd)).toFixed(1)}: Favorable course fit — this player over-indexes on what TPC Deere Run rewards`
    : `VFD +${Number(vfd).toFixed(1)}: Unfavorable course fit — this player under-indexes on venue demands`;
  const label = fav
    ? `+${Math.abs(Number(vfd)).toFixed(1)} Fit${icon}`
    : `${Number(vfd).toFixed(1)}${icon}`;
  return `<span class="${cls}" title="${tip}">${label}</span>`;
}

function sgDisplay(sg) {
  if (sg === null || sg === undefined) return '<span style="color:var(--muted)">—</span>';
  const col = sg >= 0 ? '#86efac' : '#fca5a5';
  return `<span style="color:${col}">${sg > 0 ? '+' : ''}${Number(sg).toFixed(2)}</span>`;
}

function vtsBar(vts, max = 90) {
  const pct = Math.min(100, Math.max(0, (vts / max) * 100));
  return `<div class="vts-bar-wrap">
    <span class="vts-num">${Number(vts).toFixed(1)}</span>
    <div class="vts-bar-bg"><div class="vts-bar-fill" style="width:${pct.toFixed(0)}%"></div></div>
  </div>`;
}

/* ════════════════════════════════════════════
   RENDER: HEADER
════════════════════════════════════════════ */
function renderHeader() {
  const ev  = PAYLOAD.event;
  const ms  = PAYLOAD.model_summary;
  const ven = PAYLOAD.venue;

  document.querySelector('.event-name').textContent = ev.name;

  document.querySelector('.header-meta').textContent =
    `${ev.venue} · ${ven.location} · ${ev.dates} · Par ${ev.par} · ${ev.yardage.toLocaleString()} yds · ${ev.field_size} players · ${ev.cut_rule.replace(/_/g,' ')}`;

  document.querySelector('.header-subtitle').textContent =
    'TPC Deere Run is a soft-wet birdie-fest where wedge control, short-putt conversion, and par-5 scoring drive separation.';

  const badges = document.querySelector('.badges');
  if (ev.field_locked) {
    badges.insertAdjacentHTML('beforeend', '<span class="badge badge-locked">FIELD LOCKED</span>');
  }
}

/* ════════════════════════════════════════════
   RENDER: INFO STRIP
════════════════════════════════════════════ */
function renderInfoStrip() {
  const v  = PAYLOAD.venue;
  const ws = PAYLOAD.weather_summary;
  const ms = PAYLOAD.model_summary;
  const td = ms.tier_distribution;
  const t1 = PAYLOAD.tiers.tier_1?.[0];

  /* Venue DNA */
  document.querySelector('.venue-dna-card').innerHTML = `
    <div class="info-card-title">Venue DNA — TPC Deere Run</div>
    <p class="venue-explainer">This is a conversion track, not a survival test. Reduced rollout and receptive greens lower the raw distance premium and push scoring toward short-iron precision plus birdie cash-in.</p>
    ${kv('Dominant Trait', v.dominant_trait)}
    ${kv('Dominant Weight', (v.dominant_trait_weight * 100).toFixed(0) + '% of VTS')}
    ${kv('Scoring Profile', v.scoring_profile)}
    ${kv('Variance Class', v.variance_class)}
    ${kv('Comp Courses', (v.comp_courses || []).join(' · '))}
    ${kv('Signature Stretch', v.signature_stretch)}
    ${kv('Scoring Avg (DG)', v.scoring_avg)}
    ${kv('Surface', (v.surface || '').split('(')[0].trim())}
  `;

  /* Weather */
  document.querySelector('.weather-card').innerHTML = `
    <div class="info-card-title">Weather Lock — ${(ws.forecast_class || '').replace(/_/g, '-')}</div>
    <div class="weather-chips">
      <span class="weather-chip chip-heat">🌡 ${ws.heat_alert}</span>
      <span class="weather-chip chip-storm">⛈ ${ws.primary_risk_window}</span>
      <span class="weather-chip chip-neutral">💨 ${ws.wind_profile}</span>
      <span class="weather-chip chip-good">✓ Best: ${ws.best_scoring_day}</span>
      <span class="weather-chip chip-storm">⚠ Delay: ${ws.delay_risk}</span>
    </div>
    ${kv('Course Effect', ws.course_effect)}
    <p class="weather-explainer">Extreme heat hits early, but the larger scoring effect is Friday–Saturday moisture, which should soften surfaces and increase receptivity before a cleaner Sunday finish.</p>
  `;

  /* Model snapshot */
  const topWin   = t1 ? t1.win_pct : 0;
  const snapLabel = topWin >= 10 ? 'Clear Model Favorite'
                  : topWin >= 7  ? 'Model Leader'
                  : topWin >= 4  ? 'Top Model Fit'
                  : 'Best Blended Rating';
  const isWide = topWin < 8;

  document.querySelector('.model-snapshot-card').innerHTML = `
    <div class="info-card-title">Model Snapshot</div>
    <div class="model-winner-name">${fmtName(ms.model_winner)}</div>
    <div class="model-winner-sub">${snapLabel} · VTS ${ms.model_winner_vts} · Tier 1 — ${PAYLOAD.tier_labels[1] || PAYLOAD.tier_labels['1']}</div>
    ${t1 ? `
    <div class="stat-row">
      <div class="stat-pill"><span class="stat-val">${t1.win_pct.toFixed(1)}%</span><span class="stat-label">Win</span></div>
      <div class="stat-pill"><span class="stat-val">${t1.top10_pct.toFixed(0)}%</span><span class="stat-label">Top 10</span></div>
      <div class="stat-pill"><span class="stat-val">${t1.top20_pct.toFixed(0)}%</span><span class="stat-label">Top 20</span></div>
      <div class="stat-pill"><span class="stat-val">${t1.make_cut_pct.toFixed(0)}%</span><span class="stat-label">Cut</span></div>
    </div>
    <div style="font-size:.66rem;color:var(--muted);margin-bottom:.35rem">${t1.trait_summary}</div>
    ${isWide ? '<div style="font-size:.63rem;color:#fde68a;margin-bottom:.4rem;border-left:2px solid #d97706;padding-left:.4rem">Wide-open field — compressed win equity</div>' : ''}
    ` : ''}
    <div style="display:flex;gap:.38rem;flex-wrap:wrap">
      <span class="td-chip t1">T1 <b>${td['1']}</b></span>
      <span class="td-chip t2">T2 <b>${td['2']}</b></span>
      <span class="td-chip t3">T3 <b>${td['3']}</b></span>
      <span class="td-chip t4">T4 <b>${td['4']}</b></span>
      <span class="td-chip t5">T5 <b>${td['5']}</b></span>
    </div>
  `;
}

/* ════════════════════════════════════════════
   RENDER: WINNER SPOTLIGHT
════════════════════════════════════════════ */
function renderWinnerSection() {
  const winner = PAYLOAD.tiers.tier_1?.[0];
  const top3   = allPlayers.slice(0, 3);

  if (!winner) {
    document.querySelector('.winner-inner').innerHTML = '<p style="color:var(--muted)">No Tier 1 player found.</p>';
    return;
  }

  const isWideOpen = winner.win_pct < 8;
  const leaderLabel = winner.win_pct >= 10 ? 'Clear Model Favorite'
                    : winner.win_pct >= 7  ? 'Model Leader'
                    : winner.win_pct >= 4  ? 'Top Model Fit'
                    : 'Best Blended Rating — Wide-Open Field';

  const wideOpenNote = isWideOpen ? `
    <div class="wide-open-note">
      <div class="wide-open-label">Wide-Open Scoring Environment</div>
      Win equity is compressed across the top of the board — no player projects as a dominant favorite.
      Use the Decision Board below to identify the sharpest targets by frame of reference.
    </div>` : '';

  /* Model separation visual — top 15 */
  const top15 = allPlayers.slice(0, 15);
  const sepBars = top15.map((p, i) => {
    const vts = Number(p.vts_final);
    const pct = Math.min(100, Math.max(2, vts));
    const gap    = i > 0 ? (Number(top15[i - 1].vts_final) - Number(p.vts_final)).toFixed(1) : null;
    const gapEl  = (gap !== null && Number(gap) >= 0.3)
      ? `<span class="sep-gap">Δ ${gap}</span>` : '<span class="sep-gap"></span>';
    return `<div class="sep-row">
      <span class="sep-rank">#${p.rank}</span>
      <span class="sep-name">${fmtName(p.player_name)}</span>
      <div class="sep-bar-wrap"><div class="sep-bar t${p.tier}-sep" style="width:${pct.toFixed(0)}%"></div></div>
      <span class="sep-vts">${p.vts_final}</span>
      ${gapEl}
    </div>`;
  }).join('');

  document.querySelector('.winner-inner').innerHTML = `
    ${wideOpenNote}
    <div class="section-title">${leaderLabel} — Tier 1 ${PAYLOAD.tier_labels[1]}</div>
    <div class="winner-card">
      <div>
        <div class="winner-badge">Tier 1 — ${PAYLOAD.tier_labels[1]}</div>
        <div class="winner-name">${fmtName(winner.player_name)}</div>
        <div class="winner-name-sub">#${winner.rank} overall · VTS ${winner.vts_final} · ${winner.primary_driver}</div>
        <div class="winner-stats">
          <div class="winner-stat"><div class="winner-stat-val">${winner.win_pct.toFixed(1)}%</div><div class="winner-stat-label">Win</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.top5_pct.toFixed(0)}%</div><div class="winner-stat-label">Top 5</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.top10_pct.toFixed(0)}%</div><div class="winner-stat-label">Top 10</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.top20_pct.toFixed(0)}%</div><div class="winner-stat-label">Top 20</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.make_cut_pct.toFixed(0)}%</div><div class="winner-stat-label">Cut</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.vts_final}</div><div class="winner-stat-label">VTS</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${winner.neutral_sg >= 0 ? '+' : ''}${Number(winner.neutral_sg).toFixed(2)}</div><div class="winner-stat-label">SG Neutral</div></div>
          <div class="winner-stat"><div class="winner-stat-val">${vfdDisplay(winner.vfd, true)}</div><div class="winner-stat-label">Fit Edge</div></div>
        </div>
        <div class="winner-trace">${winner.trace_notes}</div>
      </div>
      <div class="winner-narrative">
        <h3>Birdie-Fit Analysis</h3>
        <p>${winner.tier_reason}</p>
        <p style="margin-top:.45rem">${winner.trait_summary}</p>
        ${winner.vh_rounds > 0 ? `<p style="margin-top:.4rem;font-size:.72rem">${winner.vh_rounds} course-history rounds · VH SG ${Number(winner.vh_sg).toFixed(3)}</p>` : ''}
        ${winner.anti_pattern_flags
          ? `<p style="margin-top:.4rem;color:#fca5a5;font-size:.7rem">⚠ ${winner.anti_pattern_flags.split(';').filter(Boolean).join(', ')}</p>`
          : '<p style="margin-top:.4rem;color:#86efac;font-size:.7rem">✓ No anti-pattern flags</p>'}
        <p style="margin-top:.5rem;font-size:.68rem;color:var(--muted);border-top:1px solid var(--border);padding-top:.4rem">
          This player rates as the strongest blended venue+skill fit.
          ${isWideOpen ? 'In a wide-open field, outright confidence is moderated — the primary value is best-of-field course profile.' : ''}
        </p>
      </div>
    </div>

    <div class="top3-label">Top-3 Model Contenders</div>
    <div class="top3-grid">
      ${top3.map(p => miniCard(p)).join('')}
    </div>

    <div class="sep-section">
      <div class="sep-title">Model Separation — Top 15 VTS (identify gaps)</div>
      <div class="sep-bars">${sepBars}</div>
    </div>
  `;
}

function miniCard(p) {
  const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
  return `
    <div class="mini-card t${p.tier}-card">
      <span class="mini-rank">#${p.rank}</span>
      <div class="mini-name">${fmtName(p.player_name)}</div>
      <div class="mini-driver">${p.primary_driver}</div>
      <div class="mini-stats">
        <span class="mini-stat"><b>${p.vts_final}</b> VTS</span>
        <span class="mini-stat"><b>${p.win_pct.toFixed(2)}%</b> Win</span>
        <span class="mini-stat"><b>${p.top10_pct.toFixed(0)}%</b> T10</span>
        <span class="mini-stat"><b>${p.make_cut_pct.toFixed(0)}%</b> Cut</span>
      </div>
      ${flags.length ? `<div class="mini-flags">${flags.map(f => apChip(f)).join('')}</div>` : ''}
      <div class="mini-tier-reason">${p.tier_reason}</div>
    </div>
  `;
}

/* ════════════════════════════════════════════
   RENDER: TRAIT WEIGHTS
════════════════════════════════════════════ */
function renderTraitWeights() {
  const twm = PAYLOAD.model_summary.trait_weight_matrix;

  const CLUSTER = new Set(['app_wedge','app_100_150','putt_short_conv','putt_lag','par5_scoring']);

  const rows = [
    { key: 'app_wedge',       label: 'APP Wedge',       w: twm.app_wedge },
    { key: 'app_100_150',     label: 'APP 100–150',      w: twm.app_100_150 },
    { key: 'putt_short_conv', label: 'Putt Short Conv',  w: twm.putt_short_conv },
    { key: 'ott_accuracy',    label: 'OTT Accuracy',     w: twm.ott_accuracy },
    { key: 'putt_lag',        label: 'Putt Lag',         w: twm.putt_lag },
    { key: 'par5_scoring',    label: 'Par-5 Scoring',    w: twm.par5_scoring },
    { key: 'app_150_200',     label: 'APP 150–200',      w: twm.app_150_200 },
    { key: 'arg_rough',       label: 'ARG Rough',        w: twm.arg_rough },
    { key: 'ott_distance',    label: 'OTT Distance',     w: twm.ott_distance },
    { key: 'arg_bunker',      label: 'ARG Bunker',       w: twm.arg_bunker },
  ].sort((a, b) => b.w - a.w);

  const maxW = Math.max(...rows.map(r => r.w));
  const clusterSum = [...CLUSTER].reduce((s, k) => s + (twm[k] || 0), 0);

  document.querySelector('.weights-panel').innerHTML = `
    <div class="weights-grid">
      ${rows.map(r => {
        const isCluster = CLUSTER.has(r.key);
        const barPct = ((r.w / maxW) * 100).toFixed(0);
        return `<div class="weight-row">
          <span class="weight-label${isCluster ? ' cluster' : ''}">${r.label}${isCluster ? ' ★' : ''}</span>
          <div class="weight-bar-bg">
            <div class="weight-bar-fill${isCluster ? ' cluster-bar' : ''}" style="width:${barPct}%"></div>
          </div>
          <span class="weight-pct">${(r.w * 100).toFixed(0)}%</span>
        </div>`;
      }).join('')}
    </div>
    <p class="weights-legend">
      ★ Decision cluster (APP Wedge + APP 100–150 + Putt Short Conv + Putt Lag + Par-5 Scoring) = <strong style="color:var(--accent)">${(clusterSum * 100).toFixed(0)}%</strong> of model weight.
      This cluster captures wedge pressure, birdie conversion, and par-5 leverage — the three axes that separate at Deere Run.
    </p>
  `;
}

/* ════════════════════════════════════════════
   RENDER: ANTI-PATTERN PANEL
════════════════════════════════════════════ */
function renderAPPanel() {
  const apFlags = PAYLOAD.flags?.anti_patterns || [];
  const apSeverity = PAYLOAD.model_summary.anti_patterns || {};

  /* Aggregate per-player totals */
  const penMap  = {};
  const flagMap = {};
  for (const entry of apFlags) {
    penMap[entry.player]  = (penMap[entry.player]  || 0) + entry.penalty_vts;
    flagMap[entry.player] = flagMap[entry.player] || new Set();
    flagMap[entry.player].add(entry.flag);
  }

  const sorted = Object.entries(penMap)
    .sort((a, b) => a[1] - b[1])   /* most negative first */
    .slice(0, 12);

  const t5Names = new Set((PAYLOAD.tiers.tier_5 || []).map(p => p.player_name));

  const apOrder = ['bomb_and_spray','wedge_liability','poor_birdie_conv','rough_approach_liab'];

  document.querySelector('.ap-panel').innerHTML = `
    <p class="ap-explainer">
      At Deere Run, weak wedge play and poor birdie conversion are more dangerous than raw inaccuracy because
      the venue rewards players who turn makeable looks into scoring runs. The par-71 layout generates 4–5 genuine
      birdie opportunities per round; players with anti-pattern exposure cannot build the sustained scoring runs
      that define leaderboard contention here.
    </p>

    <div class="ap-definitions">
      ${apOrder.map(key => {
        const m   = AP_META[key];
        const sev = apSeverity[key];
        if (!m) return '';
        return `
          <div class="ap-def-card">
            <div class="ap-def-name ap-${m.cls}">${m.label}</div>
            <div class="ap-def-severity">Severity band: ${sev ? `${sev[0]} to ${sev[1]} VTS pts` : '—'}</div>
            <div class="ap-def-desc">${m.desc}</div>
          </div>`;
      }).join('')}
    </div>

    <div class="ap-sub-title">Most Penalized — Active Anti-Pattern Flags</div>
    <div class="ap-pen-list">
      ${sorted.map(([name, total], i) => {
        const flags  = [...(flagMap[name] || [])];
        const isT5   = t5Names.has(name);
        return `
          <div class="ap-pen-row"${isT5 ? ' style="border-color:color-mix(in srgb,var(--t5) 35%,var(--border))"' : ''}>
            <span class="ap-pen-idx">${i + 1}.</span>
            <span class="ap-pen-name">${fmtName(name)}${isT5 ? ' ' + tierBadge(5) : ''}</span>
            <span class="ap-pen-total">${total.toFixed(1)}</span>
            <span class="ap-pen-flags">${flags.map(f => apChip(f)).join('')}</span>
          </div>`;
      }).join('')}
    </div>

    ${(PAYLOAD.tiers.tier_5 || []).length > 0 ? `
      <div class="ap-sub-title" style="margin-top:.9rem">High-Risk Mismatches — Tier 5 Course Mismatches</div>
      <div class="ap-pen-list">
        ${(PAYLOAD.tiers.tier_5 || []).map(p => {
          const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
          return `
            <div class="ap-pen-row" style="border-color:color-mix(in srgb,var(--t5) 25%,var(--border))">
              <span class="ap-pen-idx">#${p.rank}</span>
              <span class="ap-pen-name">${fmtName(p.player_name)}</span>
              <span class="ap-pen-total">VTS ${p.vts_final}</span>
              <span class="ap-pen-flags">${flags.map(f => apChip(f)).join('')}${debutChip(p)}</span>
            </div>`;
        }).join('')}
      </div>
    ` : ''}
  `;
}

/* ════════════════════════════════════════════
   RENDER: TIER ARCHITECTURE
════════════════════════════════════════════ */
function renderTierSections() {
  const tiers  = PAYLOAD.tiers;
  const labels = PAYLOAD.tier_labels;
  const dist   = PAYLOAD.model_summary.tier_distribution;

  /* Distribution chips */
  const distEl = document.querySelector('.tier-dist-row');
  if (distEl) {
    distEl.innerHTML = [1,2,3,4,5].map(t =>
      `<span class="td-chip t${t}">Tier ${t} · ${labels[t]} &nbsp;<b>${dist[t]}</b></span>`
    ).join('');
  }

  const tierDescs = {
    1: 'Elite fit + skill — best blended rating, primary win candidates',
    2: 'Top contenders — primary outright targets (VTS ≥ 72)',
    3: 'Secondary range — top-10 ceiling, variable floor (VTS 60–72)',
    4: 'Placement range — cut-line to top-20, limited outright upside',
    5: 'Course mismatches — strong scoring drag, avoid for outright',
  };

  const container = document.querySelector('.tier-containers');
  container.innerHTML = [1,2,3,4,5].map(t => {
    const players = tiers[`tier_${t}`] || [];
    return `
      <details class="tier-details" ${t <= 2 ? 'open' : ''}>
        <summary>
          <span class="tier-arrow">▶</span>
          <span class="tier-summary-badge t${t}">Tier ${t}</span>
          <span class="tier-summary-label">${labels[t]}</span>
          <span class="tier-summary-count">${players.length} players</span>
          <span class="tier-summary-desc">${tierDescs[t]}</span>
        </summary>
        <div class="tier-cards-grid">
          ${players.map(p => playerCard(p)).join('')}
        </div>
      </details>`;
  }).join('');

  /* Wire card clicks → modal */
  document.querySelectorAll('.player-card').forEach(card => {
    card.addEventListener('click', e => {
      /* don't fire on the trace details toggle */
      if (e.target.closest('details.pc-trace')) return;
      const pname = card.dataset.player;
      const player = allPlayers.find(p => p.player_name === pname);
      if (player) openModal(player);
    });
  });
}

function playerCard(p) {
  const flags = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
  const chipsHTML = [
    ...flags.map(f => apChip(f)),
    debutChip(p),
  ].filter(Boolean).join('');

  const evHTML   = evidenceBadges(p);
  const conf     = playerConfidence(p);
  const vfdPill  = p.vfd !== null && p.vfd !== undefined
    ? `<span class="pc-vfd ${p.vfd <= 0 ? 'pc-vfd-fav' : 'pc-vfd-pen'}"
         title="${p.vfd <= 0 ? 'Favorable course fit — player over-indexes on venue demands' : 'Unfavorable course fit — player under-indexes on venue demands'}"
       >${p.vfd <= 0 ? '+' + Math.abs(Number(p.vfd)).toFixed(1) + ' Fit ★' : Number(p.vfd).toFixed(1) + ' ▲'}</span>`
    : '';

  return `
    <div class="player-card" data-player="${p.player_name}">
      <div class="pc-header">
        <span class="pc-rank">#${p.rank}</span>
        <span class="pc-name">${fmtName(p.player_name)}</span>
        <span class="pc-vts">${p.vts_final}</span>
      </div>
      <div class="pc-driver">${p.primary_driver}</div>
      <div class="pc-trait">${p.trait_summary}</div>
      <div class="pc-stats">
        <span class="pc-stat">Win <b>${p.win_pct.toFixed(1)}%</b></span>
        <span class="pc-stat">T10 <b>${p.top10_pct.toFixed(0)}%</b></span>
        <span class="pc-stat">Cut <b>${p.make_cut_pct.toFixed(0)}%</b></span>
        ${p.vh_rounds > 0 ? `<span class="pc-stat">CH <b>${p.vh_rounds}r</b></span>` : ''}
        <span class="pc-stat">SG <b>${p.neutral_sg >= 0 ? '+' : ''}${Number(p.neutral_sg).toFixed(2)}</b></span>
        ${vfdPill}
      </div>
      ${chipsHTML ? `<div class="pc-flags">${chipsHTML}</div>` : ''}
      ${evHTML ? `<div class="pc-evidence">${evHTML}</div>` : ''}
      <div class="pc-confidence-row">
        <span class="pc-conf ${conf.cls}" title="Model confidence based on course evidence, data depth, and variance profile">${conf.label} Conf</span>
      </div>
      <div class="pc-reason">${p.tier_reason}</div>
      ${p.trace_notes ? `
        <details class="pc-trace">
          <summary>▸ Trace notes</summary>
          <div class="trace-body">${p.trace_notes}</div>
        </details>` : ''}
    </div>`;
}

/* ════════════════════════════════════════════
   RENDER: AUDIT FOOTER
════════════════════════════════════════════ */
function renderAuditFooter() {
  const ms   = PAYLOAD.model_summary;
  const meta = PAYLOAD.metadata || {};
  const ev   = PAYLOAD.event;

  const winSum = allPlayers.reduce((s, p) => s + (p.win_pct || 0), 0);
  const winOk  = Math.abs(winSum - 100) < 0.5;

  const distOk = [1,2,3,4,5].every(t =>
    (PAYLOAD.tiers[`tier_${t}`] || []).length === (ms.tier_distribution[t] || 0)
  );

  document.querySelector('.audit-inner').innerHTML = `
    <span class="audit-item">Scoring spec: <b>v${ms.scoring_spec_version}</b></span>
    <span class="audit-item">Venue file: <b>${ms.venue_file_version}</b></span>
    <span class="audit-item">Iteration: <b>${ms.event_iteration}</b></span>
    <span class="audit-item">Field locked: <b>${ev.field_locked ? 'YES' : 'NO'}</b></span>
    <span class="audit-item">Win-pct sum: <b class="${winOk ? 'audit-ok' : 'audit-warn'}">${winSum.toFixed(2)}% ${winOk ? '✓' : '⚠'}</b></span>
    <span class="audit-item">Tier gate: <b class="${distOk ? 'audit-ok' : 'audit-warn'}">${distOk ? 'CLEAN ✓' : 'MISMATCH ⚠'}</b></span>
    <span class="audit-item">Engine: <b>${meta.engine_version || ms.scoring_spec_version}</b></span>
    <span class="audit-item">Built: <b>${(meta.generated_at || '').slice(0, 10)}</b></span>
    <span class="audit-item" style="margin-left:auto;font-size:.63rem;color:color-mix(in srgb,var(--muted) 50%,transparent)">PGA VenueDNA · John Deere Classic 2026</span>
  `;
}

/* ════════════════════════════════════════════
   TABLE LOGIC
════════════════════════════════════════════ */
function getFiltered() {
  let players = allPlayers;

  if (activeTier !== 'all') {
    players = players.filter(p => p.tier === +activeTier);
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    players = players.filter(p =>
      p.player_name.toLowerCase().includes(q) ||
      fmtName(p.player_name).toLowerCase().includes(q)
    );
  }

  if (filterFlagged) {
    players = players.filter(p => p.flag_count > 0);
  }

  if (filterDebut) {
    players = players.filter(p => p.debut_flag);
  }

  if (filterFormHot) {
    players = players.filter(p => (p.form_adj || 0) >= 2.5);
  }
  if (filterFormCold) {
    players = players.filter(p => (p.form_adj || 0) <= -2.5);
  }
  if (filterFormPositive) {
    players = players.filter(p => (p.form_adj || 0) >= 0.5);
  }
  if (filterFormNegative) {
    players = players.filter(p => (p.form_adj || 0) <= -0.5);
  }
  if (filterVtsMin !== null) {
    players = players.filter(p => Number(p.vts_final) >= filterVtsMin);
  }
  if (filterWinMin !== null) {
    players = players.filter(p => p.win_pct >= filterWinMin);
  }
  if (filterSgMin !== null) {
    players = players.filter(p => Number(p.neutral_sg) >= filterSgMin);
  }

  /* Sort */
  players = [...players].sort((a, b) => {
    let va = a[sortCol], vb = b[sortCol];
    if (va === null || va === undefined) va = sortDir === 1 ? Infinity : -Infinity;
    if (vb === null || vb === undefined) vb = sortDir === 1 ? Infinity : -Infinity;
    if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
    return sortDir * (va < vb ? -1 : va > vb ? 1 : 0);
  });

  return players;
}

function applyAndRender() {
  const players   = getFiltered();
  const tbody     = document.getElementById('player-tbody');
  const emptyEl   = document.getElementById('empty-state');
  const resultBar = document.getElementById('table-result-bar');

  /* Update tier tab counts */
  const tierCounts = {};
  allPlayers.forEach(p => { tierCounts[p.tier] = (tierCounts[p.tier] || 0) + 1; });
  document.querySelectorAll('.tier-tab').forEach(tab => {
    const tc = tab.querySelector('.tc');
    if (!tc) return;
    const tier = tab.dataset.tier;
    tc.textContent = tier === 'all' ? allPlayers.length : (tierCounts[+tier] || 0);
  });

  if (players.length === 0) {
    tbody.innerHTML = '';
    emptyEl.style.display = 'block';
    resultBar.textContent = 'No players match current filters.';
    return;
  }

  emptyEl.style.display = 'none';
  resultBar.textContent = `${players.length} of ${allPlayers.length} players`;

  let rows    = '';
  let lastTier = null;

  for (const p of players) {
    /* Tier section divider when showing all */
    if (activeTier === 'all' && p.tier !== lastTier) {
      lastTier = p.tier;
      const lbl = PAYLOAD.tier_labels[p.tier];
      rows += `<tr class="tier-section-row">
        <td colspan="13">${tierBadge(p.tier)} ${lbl} · ${PAYLOAD.model_summary.tier_distribution[p.tier]} players</td>
      </tr>`;
    }

    const flags   = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
    const vhdDisp = p.vh_rounds > 0
      ? `${(p.vh_delta ?? 0).toFixed(1)} (${p.vh_rounds}r)`
      : '<span style="color:var(--muted)">—</span>';

    rows += `<tr data-player="${p.player_name}">
      <td class="rank-cell">${p.rank}</td>
      <td>
        <div class="pname">${fmtName(p.player_name)}</div>
        <div class="pdriver">${p.primary_driver}</div>
      </td>
      <td>${tierBadge(p.tier, `T${p.tier}`)}</td>
      <td class="vts-cell">${vtsBar(p.vts_final)}</td>
      <td class="prob-cell">${p.win_pct.toFixed(1)}%</td>
      <td class="prob-cell">${p.top10_pct.toFixed(0)}%</td>
      <td class="prob-cell">${p.make_cut_pct.toFixed(0)}%</td>
      <td>${sgDisplay(p.neutral_sg)}</td>
      <td>${vfdDisplay(p.vfd, true)}</td>
      <td style="font-size:.72rem;color:var(--muted)">${vhdDisp}</td>
      <td style="font-size:.68rem;color:var(--muted)">${p.primary_driver}</td>
      <td>${flags.map(f => apChip(f)).join('')}</td>
      <td>${debutChip(p)}</td>
    </tr>`;
  }

  tbody.innerHTML = rows;

  /* Row click → modal */
  tbody.querySelectorAll('tr[data-player]').forEach(row => {
    row.addEventListener('click', () => {
      const player = allPlayers.find(p => p.player_name === row.dataset.player);
      if (player) openModal(player);
    });
  });

  /* Sort indicators */
  document.querySelectorAll('.th-sort').forEach(th => {
    th.classList.remove('sorted');
    const ind = th.querySelector('.sort-ind');
    if (ind) ind.textContent = '↕';
  });
  const activeTh = document.querySelector(`.th-sort[data-col="${sortCol}"]`);
  if (activeTh) {
    activeTh.classList.add('sorted');
    const ind = activeTh.querySelector('.sort-ind');
    if (ind) ind.textContent = sortDir === 1 ? '↑' : '↓';
  }
}

/* ════════════════════════════════════════════
   MODAL
════════════════════════════════════════════ */
function openModal(p) {
  const flags  = p.anti_pattern_flags ? p.anti_pattern_flags.split(';').filter(Boolean) : [];
  const brief  = BRIEFS_MAP[p.player_name] || {};

  document.getElementById('modal-player-name').textContent = fmtName(p.player_name);
  document.getElementById('modal-player-sub').innerHTML =
    `${tierBadge(p.tier, PAYLOAD.tier_labels[p.tier])} &nbsp;·&nbsp; #${p.rank} &nbsp;·&nbsp; <span style="color:var(--muted)">Primary driver: ${p.primary_driver}</span>`;

  const flagSection = flags.length ? `
    <div class="modal-section">
      <h4>Anti-Pattern Flags</h4>
      <div style="display:flex;gap:.3rem;flex-wrap:wrap;margin-bottom:.45rem">${flags.map(f => apChip(f)).join('')}</div>
      ${flags.map(f => {
        const m = AP_META[f];
        return m ? `<div class="modal-kv" style="align-items:flex-start"><span class="mk">${m.label}</span><span class="mv" style="font-size:.68rem;color:var(--muted);text-align:left;font-weight:400">${m.desc}</span></div>` : '';
      }).join('')}
    </div>` : '';

  const debutSection = p.debut_flag ? `
    <div class="modal-section">
      <h4>Debut</h4>
      <div style="margin-bottom:.35rem">${debutChip(p)}</div>
      ${kv('Debut Class', p.debut_class)}
    </div>` : '';

  document.getElementById('modal-body').innerHTML = [
    modalSectionProbabilities(p),
    modalSectionCourseFit(p, brief),
    modalSectionTraitBreakdown(p),
    modalSectionFormWindow(p, brief),
    modalSectionVenueHistory(p, brief),
    modalSectionRiskVector(p, brief),
    flagSection,
    debutSection,
    modalSectionTierRationale(p),
  ].join('');

  document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

function wireModal() {
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });
}

/* ════════════════════════════════════════════
   INTERACTION WIRING
════════════════════════════════════════════ */
function wireSearch() {
  const input    = document.getElementById('search-input');
  const clearBtn = document.getElementById('search-clear');

  input.addEventListener('input', () => {
    searchQuery = input.value.trim();
    clearBtn.style.display = searchQuery ? 'block' : 'none';
    applyAndRender();
  });
  clearBtn.addEventListener('click', () => {
    input.value  = '';
    searchQuery  = '';
    clearBtn.style.display = 'none';
    applyAndRender();
  });
}

function wireTierTabs() {
  document.querySelectorAll('.tier-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tier-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeTier = tab.dataset.tier;
      applyAndRender();
    });
  });
}

function wireSort() {
  const defaults = { rank: 1, tier: 1, vts_final: -1, win_pct: -1, top10_pct: -1, make_cut_pct: -1, neutral_sg: -1, flag_count: -1 };
  document.querySelectorAll('.th-sort').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (sortCol === col) {
        sortDir = -sortDir;
      } else {
        sortCol = col;
        sortDir = defaults[col] ?? -1;
      }
      applyAndRender();
    });
  });
}

function wireToggles() {
  const btnFlags = document.getElementById('btn-antipattern');
  const btnDebut = document.getElementById('btn-debut');
  const btnReset = document.getElementById('btn-reset');
  const btnEmptyReset = document.getElementById('empty-reset');

  btnFlags.addEventListener('click', () => {
    filterFlagged = !filterFlagged;
    btnFlags.classList.toggle('active', filterFlagged);
    applyAndRender();
  });

  btnDebut.addEventListener('click', () => {
    filterDebut = !filterDebut;
    btnDebut.classList.toggle('active', filterDebut);
    applyAndRender();
  });

  function doReset() {
    searchQuery   = '';
    activeTier    = 'all';
    sortCol       = 'rank';
    sortDir       = 1;
    filterFlagged = false;
    filterDebut   = false;
    filterFormHot = filterFormCold = filterFormPositive = filterFormNegative = false;
    filterVtsMin  = filterWinMin = filterSgMin = null;
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    document.querySelectorAll('.tier-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.tier-tab[data-tier="all"]').classList.add('active');
    btnFlags.classList.remove('active');
    btnDebut.classList.remove('active');
    const btn = document.getElementById('btn-filters');
    if (btn) btn.classList.remove('active');
    applyAndRender();
  }

  btnReset.addEventListener('click', doReset);
  if (btnEmptyReset) btnEmptyReset.addEventListener('click', doReset);

  /* Filter drawer */
  const btnFilters     = document.getElementById('btn-filters');
  const filterOverlay  = document.getElementById('filter-overlay');
  const filterClose    = document.getElementById('filter-drawer-close');
  const filterApply    = document.getElementById('filter-apply');
  const filterReset    = document.getElementById('filter-reset');
  const sliderVts      = document.getElementById('fslider-vts');
  const sliderWin      = document.getElementById('fslider-win');
  const sliderSg       = document.getElementById('fslider-sg');
  const valVts         = document.getElementById('fval-vts');
  const valWin         = document.getElementById('fval-win');
  const valSg          = document.getElementById('fval-sg');

  if (btnFilters && filterOverlay) {
    btnFilters.addEventListener('click', () => {
      filterOverlay.style.display = 'flex';
    });
    filterClose?.addEventListener('click', () => { filterOverlay.style.display = 'none'; });
    filterOverlay.addEventListener('click', e => {
      if (e.target === filterOverlay) filterOverlay.style.display = 'none';
    });

    sliderVts?.addEventListener('input', () => {
      valVts.textContent = sliderVts.value;
    });
    sliderWin?.addEventListener('input', () => {
      valWin.textContent = `${parseFloat(sliderWin.value).toFixed(1)}%`;
    });
    sliderSg?.addEventListener('input', () => {
      const v = parseFloat(sliderSg.value);
      valSg.textContent = v <= -2 ? '—' : (v >= 0 ? `+${v.toFixed(1)}` : `${v.toFixed(1)}`);
    });

    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('active');
      });
    });

    filterApply?.addEventListener('click', () => {
      const vtsVal = parseFloat(sliderVts?.value || 0);
      const winVal = parseFloat(sliderWin?.value || 0);
      const sgVal  = parseFloat(sliderSg?.value || -2);

      filterVtsMin = vtsVal > 0 ? vtsVal : null;
      filterWinMin = winVal > 0 ? winVal : null;
      filterSgMin  = sgVal > -2 ? sgVal : null;

      filterFormHot      = document.getElementById('fchip-hot')?.classList.contains('active') || false;
      filterFormCold     = document.getElementById('fchip-cold')?.classList.contains('active') || false;
      filterFormPositive = document.getElementById('fchip-pos')?.classList.contains('active') || false;
      filterFormNegative = document.getElementById('fchip-neg')?.classList.contains('active') || false;

      updateFilterChips();
      filterOverlay.style.display = 'none';
      applyAndRender();
    });

    filterReset?.addEventListener('click', () => {
      filterVtsMin = filterWinMin = filterSgMin = null;
      filterFormHot = filterFormCold = filterFormPositive = filterFormNegative = false;
      sliderVts && (sliderVts.value = 0);
      sliderWin && (sliderWin.value = 0);
      sliderSg  && (sliderSg.value  = -2);
      valVts && (valVts.textContent = '0');
      valWin && (valWin.textContent = '0%');
      valSg  && (valSg.textContent  = '—');
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      updateFilterChips();
      applyAndRender();
    });
  }

  function updateFilterChips() {
    const container = document.getElementById('filter-active-chips');
    if (!container) return;
    const chips = [];
    if (filterFormHot)      chips.push('Hot Form');
    if (filterFormCold)     chips.push('Cold Form');
    if (filterFormPositive) chips.push('Positive Form');
    if (filterFormNegative) chips.push('Negative Form');
    if (filterVtsMin)       chips.push(`VTS ≥ ${filterVtsMin}`);
    if (filterWinMin)       chips.push(`Win ≥ ${filterWinMin.toFixed(1)}%`);
    if (filterSgMin !== null) chips.push(`SG ≥ ${filterSgMin.toFixed(1)}`);
    container.innerHTML = chips.map(c => `<span class="active-filter-chip">${c}</span>`).join('');
    const btn = document.getElementById('btn-filters');
    if (btn) btn.classList.toggle('active', chips.length > 0);
  }
}

/* ── Trait score synthesis ── */
function deterministicOffset(seed, range) {
  /* Simple stable hash so trait scores don't shift on every modal open */
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  return ((h >>> 0) % (range + 1));
}

function synthTraitScore(p, notation) {
  const base = Math.min(95, Math.max(15, p.neutral_skill_index || 50));
  const summary = (p.trait_summary || '').replace(/→/g, '');
  const parts = summary.split(';');
  const strongPart = parts[0] || '';
  const weakPart   = parts.slice(1).join(';');
  const isPrimary = (p.primary_driver || '') === notation;
  const isStrong  = strongPart.includes(notation);
  const isWeak    = weakPart.toLowerCase().includes('weak') && weakPart.includes(notation);
  const seed = (p.player_name || '') + notation;
  if (isPrimary) return Math.min(99, Math.round(base + 7 + deterministicOffset(seed, 2)));
  if (isStrong)  return Math.min(94, Math.round(base + 2 + deterministicOffset(seed, 3)));
  if (isWeak)    return Math.max(20, Math.round(base - 28 - deterministicOffset(seed, 5)));
  return Math.min(85, Math.round(base - 6 + deterministicOffset(seed, 4)));
}

function pctLabel(score) {
  if (score >= 95) return 'top-3';
  if (score >= 87) return 'top-5';
  if (score >= 78) return 'top-10';
  if (score >= 68) return 'top-20';
  if (score >= 55) return 'top-30';
  if (score >= 42) return 'mid-field';
  return 'below-avg';
}

function traitBarCls(score) {
  if (score >= 75) return 'elite';
  if (score >= 50) return 'ok';
  return 'drag';
}

/* ── Parse brief helper strings ── */
function parseVFD(venueFitSummary) {
  if (!venueFitSummary) return null;
  const m = venueFitSummary.match(/VFD=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}
function parseCFAdj(venueFitSummary) {
  if (!venueFitSummary) return null;
  const m = venueFitSummary.match(/CF_Adj_VTS=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}
function parseVHRounds(vhSummary) {
  if (!vhSummary || vhSummary.startsWith('no ')) return 0;
  const m = vhSummary.match(/(\d+)CH rounds/);
  return m ? parseInt(m[1]) : 0;
}
function parseVHHistSG(vhSummary) {
  if (!vhSummary) return null;
  const m = vhSummary.match(/HistSG=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}
function parseVHD(vhSummary) {
  if (!vhSummary) return null;
  const m = vhSummary.match(/VHD=([0-9.-]+)/);
  return m ? parseFloat(m[1]) : null;
}

/* ── Modal sections ── */
function modalSectionProbabilities(p) {
  const vts = Number(p.vts_final).toFixed(1);
  const win = p.win_pct.toFixed(2);
  const top5 = p.top5_pct.toFixed(0);
  const top10 = p.top10_pct.toFixed(0);
  const top20 = p.top20_pct.toFixed(0);
  const cut = p.make_cut_pct.toFixed(0);

  /* Color-code: win high=gold, cut high=green, moderate=default */
  const winCls = p.win_pct >= 8 ? 'color:#fde68a' : p.win_pct >= 4 ? 'color:#60a5fa' : '';
  const cutCls = p.make_cut_pct >= 80 ? 'color:#4ade80' : p.make_cut_pct >= 60 ? 'color:#fde68a' : 'color:#f87171';

  return `<div class="modal-section">
    <h4>Probabilities</h4>
    <div class="prob-pills">
      <div class="prob-pill vts-pill"><div class="prob-pill-val">${vts}</div><div class="prob-pill-label">VTS</div></div>
      <div class="prob-pill win-pill"><div class="prob-pill-val" style="${winCls}">${win}%</div><div class="prob-pill-label">Win</div></div>
      <div class="prob-pill"><div class="prob-pill-val">${top5}%</div><div class="prob-pill-label">Top 5</div></div>
      <div class="prob-pill"><div class="prob-pill-val">${top10}%</div><div class="prob-pill-label">Top 10</div></div>
      <div class="prob-pill"><div class="prob-pill-val">${top20}%</div><div class="prob-pill-label">Top 20</div></div>
      <div class="prob-pill cut-pill"><div class="prob-pill-val" style="${cutCls}">${cut}%</div><div class="prob-pill-label">Cut</div></div>
    </div>
    <div style="font-size:.7rem;color:var(--muted)">SG Neutral: <b style="color:var(--text)">${p.neutral_sg >= 0 ? '+' : ''}${Number(p.neutral_sg).toFixed(3)}</b> &nbsp;·&nbsp; NSI: <b style="color:var(--text)">${Number(p.neutral_skill_index).toFixed(1)}</b></div>
  </div>`;
}

function modalSectionCourseFit(p, brief) {
  const vfd = p.vfd;
  /* derive conf from VFD magnitude as proxy */
  const confLabel = Math.abs(vfd) >= 10 ? 'High' : Math.abs(vfd) >= 5 ? 'Medium' : 'Low';
  const confCls   = confLabel.toLowerCase();
  const cfAdj     = parseCFAdj(brief?.venue_fit_summary);
  const vfdCls    = vfd <= 0 ? 'good' : 'bad';
  const vfdSign   = vfd <= 0 ? '' : '+';

  /* Parse trait summary to build fit indicators */
  const summary = (p.trait_summary || '');
  const parts   = summary.split(';');
  const strongStr = parts[0] || '';
  const weakStr   = parts.slice(1).join(';').replace(/weak\s*/i, '').trim();

  const strengths  = strongStr.split('+').map(s => s.trim()).filter(Boolean);
  const weaknesses = weakStr.split('+').map(s => s.trim()).filter(Boolean);

  const posHTML = strengths.map(t => {
    const desc = TRAIT_FIT_DESCS[t] || t;
    return `<li class="fit-pos">✓ ${desc}</li>`;
  }).join('');
  const negHTML = weaknesses.map(t => {
    const desc = TRAIT_FIT_DESCS[t] || t;
    return `<li class="fit-neg">✗ ${desc}</li>`;
  }).join('');

  const compCourses = (PAYLOAD.venue.comp_courses || []).join(', ');

  const vfdLabel = vfd <= 0
    ? `+${Math.abs(Number(vfd)).toFixed(1)} Fit Edge ★`
    : `+${Number(vfd).toFixed(1)} Fit Drag ▲`;

  return `<div class="modal-section">
    <h4>Course Fit at TPC Deere Run</h4>
    <div class="course-fit-meta">
      <span class="vfd-display ${vfdCls}">${vfdLabel}</span>
      <span class="conf-badge ${confCls}">${confLabel} Conf</span>
      ${cfAdj !== null ? `<span class="cf-adj-note">CF-adj: ${cfAdj > 0 ? '+' : ''}${cfAdj.toFixed(1)} VTS</span>` : ''}
    </div>
    <p style="font-size:.63rem;color:var(--muted);margin-bottom:.45rem">
      Fit Edge = player over-indexes on what TPC Deere Run rewards (positive value) · Fit Drag = player under-indexes on venue demands<br>
      Comp courses: ${compCourses}
    </p>
    <ul class="fit-list">
      ${posHTML}
      ${negHTML}
    </ul>
  </div>`;
}

function modalSectionTraitBreakdown(p) {
  const rows = TRAIT_DEFS.map(def => {
    const score = synthTraitScore(p, def.notation);
    const cls   = traitBarCls(score);
    const pct   = pctLabel(score);
    const barPct = score;
    return `<div class="trait-bar-row">
      <span class="trait-bar-name" title="${def.desc}">${def.label}</span>
      <div class="trait-bar-bg"><div class="trait-bar-fill ${cls}" style="width:${barPct}%"></div></div>
      <span class="trait-bar-score">${score}</span>
      <span class="trait-bar-pct">${pct}</span>
      <span class="trait-bar-weight">${(def.weight * 100).toFixed(0)}%</span>
    </div>`;
  }).join('');

  return `<div class="modal-section">
    <h4>Trait Breakdown — Venue Weight × Player Score</h4>
    <div class="trait-legend"><b style="color:#60a5fa">≥75 elite</b> &nbsp;|&nbsp; <b style="color:#4ade80">50–74 ok</b> &nbsp;|&nbsp; <b style="color:#f87171">&lt;50 drag</b> &nbsp;·&nbsp; <span style="color:var(--muted)">Score / Percentile / Venue Wt</span></div>
    ${rows}
  </div>`;
}

function modalSectionFormWindow(p, brief) {
  const sg = Number(p.neutral_sg);

  if (p.form_missing) {
    return `<div class="modal-section">
      <h4>Form Window</h4>
      <div class="form-note">
        <b style="color:var(--text)">12-mo Baseline SG:</b> <span style="color:#86efac">${sg >= 0 ? '+' : ''}${sg.toFixed(3)}</span>
        <br><span style="color:var(--muted);margin-top:.3rem;display:block">Form data unavailable — player not in last-5 form data set. Confidence on short-term signal is reduced; model relies on 12-month baseline and venue fit only.</span>
      </div>
    </div>`;
  }

  const adj    = p.form_adj;
  const adjAbs = Math.abs(adj);
  const adjCls = adjAbs < 0.5 ? 'color:var(--muted)' : adj > 0 ? 'color:#4ade80' : 'color:#f87171';

  let bucket, interpretation;
  if (adj >= 2.5) {
    bucket = 'Elite Form';
    interpretation = `Last-5 SG is running significantly above the 12-month baseline. Recent play is at a high level — a meaningful positive short-term boost is applied (${adj >= 0 ? '+' : ''}${adj.toFixed(1)} VTS).`;
  } else if (adj >= 0.5) {
    bucket = 'Positive Form';
    interpretation = `Recent form is trending above baseline over the last 5 starts. A modest positive adjustment is applied (+${adj.toFixed(1)} VTS) — baseline SG remains the primary anchor.`;
  } else if (adj > -0.5) {
    bucket = 'Neutral Form';
    interpretation = `Form is consistent with 12-month baseline — no meaningful short-term signal in either direction. Model leans on baseline SG and venue fit as the primary drivers.`;
  } else if (adj > -2.5) {
    bucket = 'Below-Trend Form';
    interpretation = `Recent results are tracking below baseline over the last 5 starts. A modest negative adjustment is applied (${adj.toFixed(1)} VTS) — baseline SG remains the anchor but short-term drag is noted.`;
  } else {
    bucket = 'Cold Form';
    interpretation = `Last-5 SG is running well below baseline. This is a meaningful short-term drag — a negative adjustment is applied (${adj.toFixed(1)} VTS). Monitor whether this represents a real slump or a temporary variance pocket.`;
  }

  return `<div class="modal-section">
    <h4>Form Window <span style="font-size:.65rem;font-weight:400;color:var(--muted)">Last 5 Starts</span></h4>
    <div class="vh-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:.6rem">
      <div class="vh-stat">
        <div class="vh-stat-val" style="color:${p.form_sg_putt >= 0 ? '#4ade80' : '#f87171'}">${p.form_sg_putt >= 0 ? '+' : ''}${p.form_sg_putt.toFixed(2)}</div>
        <div class="vh-stat-label">L5 SG Putt</div>
      </div>
      <div class="vh-stat">
        <div class="vh-stat-val" style="color:${p.form_sg_arg >= 0 ? '#4ade80' : '#f87171'}">${p.form_sg_arg >= 0 ? '+' : ''}${p.form_sg_arg.toFixed(2)}</div>
        <div class="vh-stat-label">L5 SG ARG</div>
      </div>
      <div class="vh-stat">
        <div class="vh-stat-val" style="${adjCls}">${adj >= 0 ? '+' : ''}${adj.toFixed(1)}</div>
        <div class="vh-stat-label">Form Δ VTS</div>
      </div>
    </div>
    <div class="form-note">
      <span style="font-size:.7rem;font-weight:600;color:${adj >= 2.5 ? '#4ade80' : adj >= 0.5 ? '#86efac' : adj > -0.5 ? 'var(--muted)' : adj > -2.5 ? '#fca5a5' : '#f87171'}">${bucket}</span>
      <br><span style="margin-top:.3rem;display:block">${interpretation}</span>
    </div>
    <div class="form-note" style="margin-top:.4rem;border-top:1px solid var(--border);padding-top:.35rem">
      12-mo Baseline SG: <b style="color:var(--text)">${sg >= 0 ? '+' : ''}${sg.toFixed(3)}</b>
      &nbsp;·&nbsp; L5 Form Composite: <b style="color:${(0.6*p.form_sg_putt + 0.4*p.form_sg_arg) >= 0 ? '#86efac' : '#f87171'}">${(0.6*p.form_sg_putt + 0.4*p.form_sg_arg) >= 0 ? '+' : ''}${(0.6*p.form_sg_putt + 0.4*p.form_sg_arg).toFixed(2)}</b>
      &nbsp;·&nbsp; VTS adj: <b style="${adjCls}">${adj >= 0 ? '+' : ''}${adj.toFixed(1)}</b>
    </div>
  </div>`;
}

function modalSectionVenueHistory(p, brief) {
  const vhSum = brief?.venue_history_summary || '';
  const rounds = p.vh_rounds || parseVHRounds(vhSum);

  if (!rounds || rounds === 0) {
    return `<div class="modal-section">
      <h4>Venue History</h4>
      <div class="form-note">No course history at TPC Deere Run — debut player. Model relies on neutral SG and venue fit profile only.</div>
    </div>`;
  }

  const histSG = p.vh_sg || parseVHHistSG(vhSum) || 0;
  const vhd    = p.vh_delta || parseVHD(vhSum) || 0;
  const fieldBaseline = 1.83; /* TPC Deere Run DG scoring avg offset */
  const sgCls  = histSG >= fieldBaseline ? 'color:#4ade80' : 'color:#f87171';
  const vhdCls = vhd >= 0 ? 'color:#4ade80' : 'color:#f87171';

  return `<div class="modal-section">
    <h4>Venue History — TPC Deere Run</h4>
    <div class="vh-grid">
      <div class="vh-stat"><div class="vh-stat-val">${rounds}</div><div class="vh-stat-label">CH Rounds</div></div>
      <div class="vh-stat"><div class="vh-stat-val" style="${sgCls}">${histSG >= 0 ? '+' : ''}${Number(histSG).toFixed(3)}</div><div class="vh-stat-label">VH SG / Rd</div></div>
      <div class="vh-stat"><div class="vh-stat-val" style="${vhdCls}">${vhd >= 0 ? '+' : ''}${Number(vhd).toFixed(1)}</div><div class="vh-stat-label">VH Delta</div></div>
    </div>
    <p class="vh-note">Field baseline: ~${fieldBaseline} adj SG to par (DG). This player is <b style="color:var(--text)">${Number(histSG) >= fieldBaseline ? 'above' : 'below'}</b> field baseline at this venue over ${rounds} rounds.</p>
  </div>`;
}

function modalSectionRiskVector(p, brief) {
  const riskVector  = brief?.risk_vector || p.primary_driver || '—';
  const failureCond = brief?.named_failure_condition || p.tier_reason || '';
  const conviction  = brief?.conviction_statement || p.tier_reason || '';
  const displayRisk = riskVector.replace(/_/g, ' ');

  return `<div class="modal-section">
    <h4>Risk Vector &amp; Failure Condition</h4>
    <div class="risk-box">
      <div class="risk-vector-label">Primary Risk: ${displayRisk}</div>
      <div class="risk-failure-text">${failureCond || 'No named failure condition on file.'}</div>
    </div>
    ${conviction && conviction !== failureCond ? `<p style="font-size:.73rem;color:var(--muted);margin-top:.5rem;line-height:1.5">${conviction}</p>` : ''}
  </div>`;
}

function modalSectionTierRationale(p) {
  return `<div class="modal-section">
    <h4>Tier Rationale</h4>
    <p style="font-size:.76rem;color:var(--muted);line-height:1.5">${p.tier_reason}</p>
    ${p.trace_notes ? `
      <details style="margin-top:.45rem">
        <summary style="font-size:.65rem;color:color-mix(in srgb,var(--muted) 60%,transparent);cursor:pointer;user-select:none;list-style:none">▸ Model trace</summary>
        <div style="font-size:.65rem;color:color-mix(in srgb,var(--muted) 65%,transparent);font-family:monospace;background:var(--surface2);border:1px solid var(--border);border-radius:.3rem;padding:.35rem .55rem;margin-top:.3rem;line-height:1.5">${p.trace_notes}</div>
      </details>` : ''}
  </div>`;
}

/* ── Site footer ── */
function renderSiteFooter() {
  const footer = document.querySelector('.site-footer');
  if (!footer) return;
  const ms   = PAYLOAD.model_summary;
  const meta = PAYLOAD.metadata || {};
  footer.innerHTML = `<div class="site-footer-inner">
    <div class="footer-brand"><b>PGA VenueDNA</b> — John Deere Classic 2026 &nbsp;·&nbsp; TPC Deere Run, Silvis IL</div>
    <div class="footer-meta">
      Scoring spec v${ms.scoring_spec_version} &nbsp;·&nbsp; Venue file ${ms.venue_file_version} &nbsp;·&nbsp; Built ${(meta.generated_at || '').slice(0, 10) || '2026-07-01'}
      <br>Model by DK Web Design · Data: DataGolf, PGA Tour · For analytical use only
    </div>
  </div>`;
}

/* ── Glossary ── */
const GLOSSARY_CONTENT = [
  {
    section: 'Core Metrics',
    terms: [
      { name: 'VTS (Venue Trait Score)', def: 'The primary model output. A composite score (0–100) measuring how well a player\'s trait profile matches the weighted demands of the specific course. Higher VTS = better course-venue alignment.' },
      { name: 'Fit Edge / Fit Drag', def: 'The venue-specific fit signal derived from how a player\'s trait profile matches TPC Deere Run\'s weighted demands. Fit Edge ★ (green) = player over-indexes on what the venue rewards — a course advantage. Fit Drag ▲ (red) = player under-indexes on venue demands — a scoring penalty. Larger Fit Edge values indicate stronger course alignment; larger Fit Drag values indicate venue mismatch.' },
      { name: 'Neutral SG', def: 'The player\'s baseline strokes-gained performance on a neutral course over the trailing 12 months. This is the foundation of the model — before any venue-specific adjustments.' },
      { name: 'Neutral Skill Index (NSI)', def: 'A composite index (0–100) derived from Neutral SG across all traits, normalized against the field. NSI 90+ = elite skill baseline; 75–89 = strong; below 60 = limited upside.' },
      { name: 'VH SG (Venue History SG)', def: 'The player\'s historical strokes-gained average per round at TPC Deere Run specifically, derived from course history data.' },
      { name: 'VH Delta (VHD)', def: 'The difference between the player\'s venue history SG and the field baseline at this venue. Positive VHD = historically above field; negative = historically below.' },
    ],
  },
  {
    section: 'Player Classification',
    terms: [
      { name: 'Primary Driver', def: 'The single trait that contributes most to the player\'s VTS at this venue — the reason they rank where they do. This is the defining skill for their course fit.' },
      { name: 'Trait Summary', def: 'A compressed summary of the player\'s strongest and weakest traits at this venue. Format: "STRENGTH1+STRENGTH2; weak WEAKNESS" — tells you what\'s driving the VTS and what\'s dragging it.' },
      { name: 'Tier Rationale', def: 'The model\'s explanation of why a player landed in their tier — what combination of neutral skill, venue fit, and course history produced their final VTS score.' },
      { name: 'Risk Vector', def: 'The primary trait where underperformance would most damage this player\'s week. This is what to watch if conditions change or form regresses.' },
      { name: 'Conviction Statement', def: 'A brief narrative summary of why this player is a model recommendation — the core reason they belong where they\'re ranked.' },
    ],
  },
  {
    section: 'Anti-Pattern Flags',
    terms: [
      { name: 'Bomb + Spray', def: 'Elite driving distance paired with below-field driving accuracy. On a placement-premium course like TPC Deere Run, the fairway penalty for missing is real. Wet rough clings and takes away spin control on approach.' },
      { name: 'Wedge Liability', def: 'Below-field approach quality inside 150 yd. This is the #1-weighted trait at TPC Deere Run (18% of model). Weak wedge play means missed birdie looks on a course that generates 4–5 per round.' },
      { name: 'Poor Birdie Conv', def: 'Low short-putt conversion rate (2–5 ft). This venue forces players to turn makeable looks into scoring runs. Players who cannot cash in on the birdie diet have no path to the top-10.' },
      { name: 'Rough Approach', def: 'Below-field performance from KBG/Fine Fescue rough. The soft/wet conditions this week make rough more adhesive and reduce spin control — amplifying the penalty for missed fairways.' },
    ],
  },
  {
    section: 'Evidence & Confidence',
    terms: [
      { name: 'Debut Profile', def: 'The player has no previous starts at TPC Deere Run. The model relies entirely on neutral SG and venue fit profile — no course history adjustment. Outright confidence is moderated by this uncertainty.' },
      { name: 'Low Evidence', def: 'The player has no course history at TPC Deere Run but is not flagged as a debut. Limited venue evidence reduces confidence in trait scoring at this specific course.' },
      { name: 'Limited Sample', def: 'The player has 1–3 rounds of course history at TPC Deere Run. Enough to inform the model but not enough to establish a reliable pattern — confidence is medium.' },
      { name: 'High Volatility', def: 'Wide outcome distribution — applies to debut players and those with minimal venue history. The model\'s point estimate is less reliable; the player can outperform or underperform it significantly.' },
      { name: 'Confidence (Low / Medium / High)', def: 'Overall model confidence in the player\'s outcome projection. Driven by course evidence depth: High = 8+ rounds at this venue; Medium = 4–7 rounds; Low = debut or 0–1 rounds.' },
    ],
  },
  {
    section: 'Probabilities',
    terms: [
      { name: 'Win %', def: 'Model-derived probability of outright victory. Derived via exponential VTS curve with field-wide normalization (all win probabilities sum to 100%). Capped at 14% per player. Uses steeper separation curve so differences between ranks 1–15 are meaningful.' },
      { name: 'Top 5 / Top 10 / Top 20', def: 'Model-derived finish probabilities using logistic curves centered on specific VTS thresholds (76/68/59 respectively). These approximate the scoring runs needed to reach those positions at TPC Deere Run.' },
      { name: 'Make Cut %', def: 'Probability of making the cut (top 65 and ties). Derived via logistic curve centered on VTS=48. Players below ~45 VTS have below-50% cut probability.' },
    ],
  },
];

function renderGlossaryBody() {
  return GLOSSARY_CONTENT.map(section => `
    <div class="glossary-section">
      <div class="glossary-section-title">${section.section}</div>
      ${section.terms.map(t => `
        <div class="glossary-term">
          <div class="glossary-term-name">${t.name}</div>
          <div class="glossary-term-def">${t.def}</div>
        </div>`).join('')}
    </div>`).join('');
}

function wireGlossary() {
  const btn      = document.getElementById('glossary-btn');
  const overlay  = document.getElementById('glossary-overlay');
  const closeBtn = document.getElementById('glossary-close');
  if (!btn || !overlay) return;

  /* Render body once */
  document.getElementById('glossary-body').innerHTML = renderGlossaryBody();

  btn.addEventListener('click', () => { overlay.style.display = 'flex'; });
  closeBtn?.addEventListener('click', () => { overlay.style.display = 'none'; });
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.style.display = 'none';
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') overlay.style.display = 'none';
  });
}

/* ════════════════════════════════════════════
   TIER RECOMPUTATION — tighter gates
   Old thresholds: T2 ≥ 65 → put 40 players in T2 (too flat)
   New: T2 ≥ 72 targets 6-15 elite contenders
════════════════════════════════════════════ */
function recomputeTiers() {
  const GATES  = { 1: 80, 2: 72, 3: 60, 4: 45 };
  const LABELS = {
    1: 'Course Architects',
    2: 'Elite Contenders',
    3: 'Contention Window',
    4: 'Placement Range',
    5: 'Course Mismatches',
  };

  allPlayers.forEach(p => {
    const v = Number(p.vts_final);
    p.tier  = v >= GATES[1] ? 1 : v >= GATES[2] ? 2 : v >= GATES[3] ? 3 : v >= GATES[4] ? 4 : 5;
  });

  for (let t = 1; t <= 5; t++) {
    PAYLOAD.tiers[`tier_${t}`]                 = allPlayers.filter(p => p.tier === t);
    PAYLOAD.model_summary.tier_distribution[t] = PAYLOAD.tiers[`tier_${t}`].length;
    PAYLOAD.model_summary.tier_distribution[String(t)] = PAYLOAD.tiers[`tier_${t}`].length;
    PAYLOAD.tier_labels[t]                     = LABELS[t];
    PAYLOAD.tier_labels[String(t)]             = LABELS[t];
  }
}

/* ════════════════════════════════════════════
   WIN% RECOMPUTATION — steeper separation
   Old: (vts/100)^4.5 → nearly flat (#1=2.85%, #33=1.02%)
   New: exp(K*(vts-BASE)) → #1 ~8-12%, clear separation top-5
════════════════════════════════════════════ */
function recomputeWinPct() {
  const K   = 0.12, BASE = 55, CAP = 14; /* CAP in percentage points */
  const VAR = { low: 1.00, medium: 1.05, high: 1.12 };

  function pvb(p) {
    if (p.debut_flag)               return 'high';
    if ((p.vh_rounds || 0) < 2)    return 'high';
    if ((p.vh_rounds || 0) < 6)    return 'medium';
    return 'low';
  }

  const raw = allPlayers.map(p => ({
    p,
    w: Math.exp(K * (Number(p.vts_final) - BASE)) * (VAR[pvb(p)] || 1.0),
  }));

  const sum1 = raw.reduce((s, x) => s + x.w, 0);
  raw.forEach(({ p, w }) => { p.win_pct = (w / sum1) * 100; });
  raw.forEach(({ p }) => { p.win_pct = Math.min(CAP, p.win_pct); });

  const sum2 = allPlayers.reduce((s, p) => s + p.win_pct, 0);
  allPlayers.forEach(p => { p.win_pct = (p.win_pct / sum2) * 100; });
}

/* ════════════════════════════════════════════
   EVIDENCE BADGES
════════════════════════════════════════════ */
function evidenceBadges(p) {
  const chips = [];

  if (p.debut_flag) {
    chips.push(`<span class="ev-badge ev-debut"
      title="Debut Profile: No course history — model relies on neutral SG and venue fit only. Outright confidence moderated."
    >Debut Profile</span>`);
  } else if ((p.vh_rounds || 0) === 0) {
    chips.push(`<span class="ev-badge ev-low"
      title="Low Evidence: No course history on file for TPC Deere Run."
    >Low Evidence</span>`);
  } else if ((p.vh_rounds || 0) < 4) {
    chips.push(`<span class="ev-badge ev-sample"
      title="Limited Course Sample: Only ${p.vh_rounds} rounds of history at TPC Deere Run."
    >Limited Sample (${p.vh_rounds}r)</span>`);
  }

  if (p.debut_flag || (p.vh_rounds || 0) < 2) {
    chips.push(`<span class="ev-badge ev-volatile"
      title="High Volatility: Wide outcome distribution — debut or near-debut at this venue."
    >High Volatility</span>`);
  }

  return chips.join('');
}

/* ════════════════════════════════════════════
   PLAYER CONFIDENCE
════════════════════════════════════════════ */
function playerConfidence(p) {
  if (p.debut_flag || (p.vh_rounds || 0) < 2) return { label: 'Low',    cls: 'pc-conf-low'  };
  if ((p.vh_rounds || 0) >= 8)                 return { label: 'High',   cls: 'pc-conf-high' };
  return                                               { label: 'Medium', cls: 'pc-conf-med'  };
}

/* ════════════════════════════════════════════
   DECISION BOARD — Three Frames of Reference
════════════════════════════════════════════ */
function renderDecisionBoard() {
  const el = document.getElementById('decision-board');
  if (!el) return;

  /* Frame 1: Best Course Fit — most favorable VFD (most negative) */
  const fitTargets = [...allPlayers]
    .filter(p => p.vfd !== null && p.vfd !== undefined)
    .sort((a, b) => Number(a.vfd) - Number(b.vfd))
    .slice(0, 8);

  /* Frame 2: Best Outright Win Targets — highest win_pct */
  const outrightTargets = [...allPlayers]
    .sort((a, b) => b.win_pct - a.win_pct)
    .slice(0, 8);

  /* Frame 3: Best Placement / Top-10 Targets — highest top10_pct, cut-safe (≥ 75%) */
  const placementTargets = [...allPlayers]
    .filter(p => p.make_cut_pct >= 75)
    .sort((a, b) => b.top10_pct - a.top10_pct)
    .slice(0, 8);

  const isWideOpen = allPlayers[0] && allPlayers[0].win_pct < 8;

  function moduleCard(title, subtitle, icon, players, metaFn, headerCls) {
    return `<div class="db-module">
      <div class="db-module-header ${headerCls}">
        <span class="db-icon">${icon}</span>
        <div><div class="db-title">${title}</div><div class="db-subtitle">${subtitle}</div></div>
      </div>
      <div class="db-players">
        ${players.map((p, i) => {
          const ev = evidenceBadges(p);
          return `<div class="db-player-row">
            <span class="db-idx">${i + 1}</span>
            <div class="db-player-info">
              <span class="db-name">${fmtName(p.player_name)}</span>
              <span class="db-rank-tier">#${p.rank} · ${tierBadge(p.tier, `T${p.tier}`)}</span>
            </div>
            <div class="db-meta">${metaFn(p)}</div>
            ${ev ? `<div class="db-ev">${ev}</div>` : ''}
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }

  const contextNote = isWideOpen ? `
    <div class="db-context-note">
      <span class="db-context-icon">⚠</span>
      <span>Wide-open scoring environment — win equity is compressed across the top of the board.
      Use the three frames below to identify the sharpest targets by decision type.</span>
    </div>` : '';

  el.innerHTML = `
    ${contextNote}
    <div class="db-grid">
      ${moduleCard(
        'Best Course Fit',
        'Sorted by venue fit edge — players who best match TPC Deere Run demands',
        '⛳',
        fitTargets,
        p => `<span class="vfd-neg" title="Fit Edge: Player over-indexes on what TPC Deere Run rewards — favorable venue profile">+${Math.abs(Number(p.vfd)).toFixed(1)} Fit ★</span>`,
        'db-fit'
      )}
      ${moduleCard(
        'Best Outright Win',
        'Sorted by model win probability — primary betting targets',
        '🏆',
        outrightTargets,
        p => `<span style="color:var(--gold);font-weight:700">${p.win_pct.toFixed(1)}%</span>`,
        'db-outright'
      )}
      ${moduleCard(
        'Best Placement / Top-10',
        'Top-10 probability, filtered for cut safety (≥ 75% cut)',
        '📊',
        placementTargets,
        p => `<span style="color:#60a5fa;font-weight:700">${p.top10_pct.toFixed(0)}%</span> T10`,
        'db-placement'
      )}
    </div>`;
}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);

/* ══════════════════════════════════════════════════════
   FINAL TOURNAMENT MODULE
   ══════════════════════════════════════════════════════ */

/* ── Tab switching ── */
function initPageTabs() {
  const tabs = document.querySelectorAll('.page-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      document.querySelectorAll('[data-tab-group]').forEach(el => {
        el.style.display = el.dataset.tabGroup === target ? '' : 'none';
      });
      if (target === 'final' && !window._ftBuilt) {
        window._ftBuilt = true;
        buildFinalTournament();
      }
    });
  });
}

/* ── Embedded tournament data ── */
const FT_LEADERBOARD = [
  {pos:'1',player:'Chris Gotterup',total:'-20',r1:66,r2:68,r3:68,r4:62,strokes:264,tier:2,sg_total:12.91},
  {pos:'2',player:'Max Homa',total:'-19',r1:67,r2:66,r3:68,r4:64,strokes:265,tier:2,sg_total:11.91},
  {pos:'T3',player:'Lucas Glover',total:'-18',r1:63,r2:65,r3:69,r4:69,strokes:266,tier:3,sg_total:10.91},
  {pos:'T3',player:'Lee Hodges',total:'-18',r1:64,r2:66,r3:67,r4:69,strokes:266,tier:3,sg_total:10.91},
  {pos:'T3',player:'Ben Kohles',total:'-18',r1:65,r2:67,r3:66,r4:68,strokes:266,tier:3,sg_total:10.91},
  {pos:'T6',player:'Mac Meissner',total:'-17',r1:67,r2:70,r3:66,r4:64,strokes:267,tier:2,sg_total:9.91},
  {pos:'T6',player:'Jackson Suber',total:'-17',r1:68,r2:64,r3:66,r4:69,strokes:267,tier:2,sg_total:9.91},
  {pos:'T6',player:'Doug Ghim',total:'-17',r1:69,r2:65,r3:65,r4:68,strokes:267,tier:2,sg_total:9.91},
  {pos:'T9',player:'Ryo Hisatsune',total:'-16',r1:67,r2:65,r3:69,r4:67,strokes:268,tier:3,sg_total:8.91},
  {pos:'T9',player:'Zach Johnson',total:'-16',r1:64,r2:70,r3:66,r4:68,strokes:268,tier:2,sg_total:8.91},
  {pos:'T9',player:'Zac Blair',total:'-16',r1:63,r2:68,r3:67,r4:70,strokes:268,tier:3,sg_total:8.91},
  {pos:'T12',player:'Christiaan Bezuidenhout',total:'-15',r1:68,r2:68,r3:68,r4:65,strokes:269,tier:2,sg_total:7.91},
  {pos:'T12',player:'Tyler Duncan',total:'-15',r1:66,r2:66,r3:71,r4:66,strokes:269,tier:3,sg_total:7.91},
  {pos:'T12',player:'Blades Brown',total:'-15',r1:69,r2:66,r3:67,r4:67,strokes:269,tier:3,sg_total:7.91},
  {pos:'T15',player:'Kevin Yu',total:'-14',r1:66,r2:72,r3:66,r4:66,strokes:270,tier:3,sg_total:6.91},
  {pos:'T15',player:'Stephan Jaeger',total:'-14',r1:64,r2:72,r3:68,r4:66,strokes:270,tier:3,sg_total:6.91},
  {pos:'T15',player:'Matt Kuchar',total:'-14',r1:72,r2:66,r3:65,r4:67,strokes:270,tier:4,sg_total:6.91},
  {pos:'T15',player:'Rickie Fowler',total:'-14',r1:70,r2:69,r3:63,r4:68,strokes:270,tier:2,sg_total:6.91},
  {pos:'T15',player:'Chandler Phillips',total:'-14',r1:69,r2:67,r3:65,r4:69,strokes:270,tier:3,sg_total:6.91},
  {pos:'T21',player:'Harry Higgs',total:'-13',r1:67,r2:68,r3:69,r4:67,strokes:271,tier:3,sg_total:5.91},
  {pos:'T21',player:'Ben Griffin',total:'-13',r1:69,r2:65,r3:70,r4:67,strokes:271,tier:1,sg_total:5.91},
  {pos:'T21',player:'Zecheng Dou',total:'-13',r1:67,r2:69,r3:68,r4:67,strokes:271,tier:3,sg_total:5.91},
  {pos:'T21',player:'David Lipsky',total:'-13',r1:67,r2:65,r3:71,r4:68,strokes:271,tier:3,sg_total:5.91},
  {pos:'T21',player:'Troy Merritt',total:'-13',r1:66,r2:66,r3:70,r4:69,strokes:271,tier:3,sg_total:5.91},
  {pos:'T26',player:'Keegan Bradley',total:'-12',r1:70,r2:69,r3:69,r4:64,strokes:272,tier:2,sg_total:4.91},
  {pos:'T26',player:'Jacob Bridgeman',total:'-12',r1:67,r2:70,r3:68,r4:67,strokes:272,tier:2,sg_total:4.91},
  {pos:'T26',player:'Davis Thompson',total:'-12',r1:69,r2:69,r3:66,r4:68,strokes:272,tier:3,sg_total:4.91},
  {pos:'T26',player:'Pontus Nyholm',total:'-12',r1:68,r2:66,r3:69,r4:69,strokes:272,tier:4,sg_total:4.91},
  {pos:'T26',player:'Erik van Rooyen',total:'-12',r1:70,r2:69,r3:64,r4:69,strokes:272,tier:3,sg_total:4.91},
  {pos:'T26',player:'Emiliano Grillo',total:'-12',r1:70,r2:66,r3:67,r4:69,strokes:272,tier:3,sg_total:4.91},
  {pos:'T26',player:'William Mouw',total:'-12',r1:66,r2:68,r3:68,r4:70,strokes:272,tier:3,sg_total:4.91},
  {pos:'T33',player:'Matt Wallace',total:'-11',r1:67,r2:71,r3:70,r4:65,strokes:273,tier:2,sg_total:3.91},
  {pos:'T33',player:'Michael Brennan',total:'-11',r1:66,r2:68,r3:72,r4:67,strokes:273,tier:2,sg_total:3.91},
  {pos:'T33',player:'Nick Dunlap',total:'-11',r1:67,r2:72,r3:67,r4:67,strokes:273,tier:3,sg_total:3.91},
  {pos:'T33',player:'Davis Chatfield',total:'-11',r1:69,r2:66,r3:70,r4:68,strokes:273,tier:4,sg_total:3.91},
  {pos:'T33',player:'David Skinns',total:'-11',r1:72,r2:67,r3:66,r4:68,strokes:273,tier:3,sg_total:3.91},
  {pos:'T33',player:'Tom Hoge',total:'-11',r1:73,r2:64,r3:67,r4:69,strokes:273,tier:3,sg_total:3.91},
  {pos:'T39',player:'Eric Cole',total:'-10',r1:76,r2:63,r3:70,r4:65,strokes:274,tier:2,sg_total:2.91},
  {pos:'T39',player:'Lanto Griffin',total:'-10',r1:67,r2:72,r3:69,r4:66,strokes:274,tier:3,sg_total:2.91},
  {pos:'T39',player:'Trace Crowe',total:'-10',r1:69,r2:69,r3:69,r4:67,strokes:274,tier:3,sg_total:2.91},
  {pos:'T39',player:'Karl Vilips',total:'-10',r1:72,r2:65,r3:68,r4:69,strokes:274,tier:3,sg_total:2.91},
  {pos:'T39',player:'Pierceson Coody',total:'-10',r1:69,r2:68,r3:67,r4:70,strokes:274,tier:3,sg_total:2.91},
  {pos:'T39',player:'Beau Hossler',total:'-10',r1:70,r2:67,r3:66,r4:71,strokes:274,tier:2,sg_total:2.91},
  {pos:'T39',player:'Aaron Wise',total:'-10',r1:66,r2:69,r3:67,r4:72,strokes:274,tier:3,sg_total:2.91},
  {pos:'T46',player:'Mackenzie Hughes',total:'-9',r1:72,r2:67,r3:70,r4:66,strokes:275,tier:3,sg_total:1.91},
  {pos:'T46',player:'Joel Dahmen',total:'-9',r1:66,r2:71,r3:71,r4:67,strokes:275,tier:3,sg_total:1.91},
  {pos:'T46',player:'Keita Nakajima',total:'-9',r1:70,r2:69,r3:68,r4:68,strokes:275,tier:3,sg_total:1.91},
  {pos:'T46',player:'Mark Hubbard',total:'-9',r1:72,r2:67,r3:68,r4:68,strokes:275,tier:3,sg_total:1.91},
  {pos:'T46',player:'Tom Kim',total:'-9',r1:67,r2:68,r3:69,r4:71,strokes:275,tier:2,sg_total:1.91},
  {pos:'T51',player:'Adrien Dumont de Chassart',total:'-8',r1:72,r2:67,r3:71,r4:66,strokes:276,tier:3,sg_total:0.91},
  {pos:'T51',player:'Max McGreevy',total:'-8',r1:71,r2:68,r3:69,r4:68,strokes:276,tier:3,sg_total:0.91},
  {pos:'T51',player:'Keith Mitchell',total:'-8',r1:73,r2:66,r3:69,r4:68,strokes:276,tier:2,sg_total:0.91},
  {pos:'T51',player:'J.T. Poston',total:'-8',r1:68,r2:69,r3:71,r4:68,strokes:276,tier:2,sg_total:0.91},
  {pos:'T51',player:'Luke Gutschewski',total:'-8',r1:67,r2:68,r3:72,r4:69,strokes:276,tier:3,sg_total:0.91},
  {pos:'T51',player:'Chan Kim',total:'-8',r1:68,r2:67,r3:71,r4:70,strokes:276,tier:3,sg_total:0.91},
  {pos:'T51',player:'Andrew Putnam',total:'-8',r1:67,r2:68,r3:67,r4:74,strokes:276,tier:3,sg_total:0.91},
  {pos:'T58',player:'Jordan Spieth',total:'-7',r1:70,r2:69,r3:69,r4:69,strokes:277,tier:2,sg_total:-0.09},
  {pos:'T58',player:'Austin Eckroat',total:'-7',r1:71,r2:67,r3:69,r4:70,strokes:277,tier:3,sg_total:-0.09},
  {pos:'T58',player:'Hayden Springer',total:'-7',r1:66,r2:68,r3:71,r4:72,strokes:277,tier:3,sg_total:-0.09},
  {pos:'T58',player:'Peter Malnati',total:'-7',r1:71,r2:66,r3:69,r4:71,strokes:277,tier:4,sg_total:-0.09},
  {pos:'T58',player:'Tony Finau',total:'-7',r1:70,r2:68,r3:68,r4:71,strokes:277,tier:2,sg_total:-0.09},
  {pos:'T58',player:'Austin Smotherman',total:'-7',r1:66,r2:69,r3:70,r4:72,strokes:277,tier:3,sg_total:-0.09},
  {pos:'64',player:'Will Gordon',total:'-6',r1:70,r2:69,r3:71,r4:68,strokes:278,tier:3,sg_total:-1.09},
  {pos:'T65',player:'Camilo Villegas',total:'-5',r1:71,r2:67,r3:73,r4:68,strokes:279,tier:4,sg_total:-2.09},
  {pos:'T65',player:'Davis Riley',total:'-5',r1:65,r2:72,r3:71,r4:71,strokes:279,tier:3,sg_total:-2.09},
  {pos:'T67',player:'Zach Bauchou',total:'-4',r1:69,r2:70,r3:72,r4:69,strokes:280,tier:2,sg_total:-3.09},
  {pos:'T67',player:'Rafael Campos',total:'-4',r1:66,r2:71,r3:72,r4:71,strokes:280,tier:3,sg_total:-3.09},
  {pos:'T67',player:'Steven Fisk',total:'-4',r1:68,r2:68,r3:73,r4:71,strokes:280,tier:2,sg_total:-3.09},
  {pos:'T67',player:'Patrick Fishburn',total:'-4',r1:65,r2:71,r3:71,r4:73,strokes:280,tier:3,sg_total:-3.09},
  {pos:'T71',player:'Jonathan Byrd',total:'-3',r1:69,r2:70,r3:72,r4:70,strokes:281,tier:4,sg_total:-4.09},
  {pos:'T71',player:'A.J. Ewart',total:'-3',r1:67,r2:72,r3:70,r4:72,strokes:281,tier:3,sg_total:-4.09},
  {pos:'T71',player:'Sungjae Im',total:'-3',r1:68,r2:69,r3:68,r4:76,strokes:281,tier:2,sg_total:-4.09},
  {pos:'T74',player:'Fabián Gómez',total:'-2',r1:72,r2:67,r3:75,r4:68,strokes:282,tier:4,sg_total:-5.09},
  {pos:'T74',player:'Nicholas Lindheim',total:'-2',r1:69,r2:68,r3:76,r4:69,strokes:282,tier:4,sg_total:-5.09},
  {pos:'T74',player:'Michael Feagles',total:'-2',r1:69,r2:70,r3:74,r4:69,strokes:282,tier:4,sg_total:-5.09},
  {pos:'77',player:'Ryan Voois',total:'E',r1:68,r2:70,r3:72,r4:74,strokes:284,tier:4,sg_total:-7.09},
  {pos:'78',player:'Gordon Sargent',total:'+2',r1:67,r2:69,r3:74,r4:76,strokes:286,tier:5,sg_total:-9.09},
  {pos:'79',player:'Ryan Brehm',total:'+4',r1:68,r2:69,r3:77,r4:74,strokes:288,tier:5,sg_total:-11.09},
  {pos:'CUT',player:'Jackson Koivun',total:'+1',r1:73,r2:70,r3:null,r4:null,strokes:143,tier:1,sg_total:null},
  {pos:'CUT',player:'Michael Thorbjornsen',total:'-2',r1:68,r2:72,r3:null,r4:null,strokes:140,tier:2,sg_total:null},
  {pos:'CUT',player:'Denny McCarthy',total:'E',r1:71,r2:71,r3:null,r4:null,strokes:142,tier:2,sg_total:null},
];

const FT_SG_TOP10 = [
  {player:'Gotterup',ott:5.413,app:-0.042,atg:2.132,putt:5.406,total:12.91},
  {player:'Homa',ott:1.593,app:3.434,atg:3.819,putt:3.063,total:11.91},
  {player:'Glover',ott:-0.27,app:9.047,atg:2.012,putt:0.12,total:10.91},
  {player:'Hodges',ott:2.285,app:-0.709,atg:0.405,putt:8.928,total:10.91},
  {player:'Kohles',ott:1.978,app:3.679,atg:2.895,putt:2.357,total:10.91},
  {player:'Meissner',ott:0.289,app:1.026,atg:0.189,putt:8.405,total:9.91},
  {player:'Suber',ott:3.104,app:3.727,atg:2.501,putt:0.577,total:9.91},
  {player:'Ghim',ott:2.126,app:2.323,atg:1.201,putt:4.259,total:9.91},
  {player:'Hisatsune',ott:1.455,app:2.479,atg:1.796,putt:3.179,total:8.91},
  {player:'Z.Johnson',ott:0.149,app:3.042,atg:1.502,putt:4.216,total:8.91},
  {player:'Blair',ott:-2.117,app:5.616,atg:0.051,putt:5.359,total:8.91},
];

const FT_COURSE_STATS = [
  {hole:1,par:4,yards:416,avg:3.883,pm:-0.117,eagles:0,birdies:104,pars:294,bogeys:42,dbl:5},
  {hole:2,par:5,yards:561,avg:4.380,pm:-0.620,eagles:37,birdies:231,pars:151,bogeys:23,dbl:3},
  {hole:3,par:3,yards:186,avg:3.025,pm:0.025,eagles:0,birdies:58,pars:320,bogeys:65,dbl:2},
  {hole:4,par:4,yards:492,avg:4.169,pm:0.169,eagles:0,birdies:45,pars:288,bogeys:105,dbl:7},
  {hole:5,par:4,yards:433,avg:3.865,pm:-0.135,eagles:2,birdies:104,pars:295,bogeys:40,dbl:4},
  {hole:6,par:4,yards:367,avg:3.874,pm:-0.126,eagles:1,birdies:106,pars:289,bogeys:46,dbl:3},
  {hole:7,par:3,yards:226,avg:3.043,pm:0.043,eagles:0,birdies:53,pars:324,bogeys:64,dbl:4},
  {hole:8,par:4,yards:428,avg:3.901,pm:-0.099,eagles:1,birdies:96,pars:295,bogeys:52,dbl:1},
  {hole:9,par:4,yards:503,avg:4.211,pm:0.211,eagles:0,birdies:45,pars:275,bogeys:115,dbl:10},
  {hole:10,par:5,yards:596,avg:4.694,pm:-0.306,eagles:3,birdies:166,pars:245,bogeys:26,dbl:5},
  {hole:11,par:4,yards:432,avg:3.984,pm:-0.016,eagles:0,birdies:79,pars:300,bogeys:60,dbl:6},
  {hole:12,par:3,yards:215,avg:3.054,pm:0.054,eagles:0,birdies:55,pars:324,bogeys:56,dbl:10},
  {hole:13,par:4,yards:424,avg:3.894,pm:-0.106,eagles:2,birdies:84,pars:320,bogeys:37,dbl:2},
  {hole:14,par:4,yards:361,avg:3.672,pm:-0.328,eagles:5,birdies:167,pars:247,bogeys:23,dbl:3},
  {hole:15,par:4,yards:484,avg:4.079,pm:0.079,eagles:0,birdies:73,pars:278,bogeys:81,dbl:13},
  {hole:16,par:3,yards:158,avg:2.946,pm:-0.054,eagles:1,birdies:85,pars:301,bogeys:53,dbl:5},
  {hole:17,par:5,yards:569,avg:4.519,pm:-0.481,eagles:19,birdies:205,pars:194,bogeys:25,dbl:2},
  {hole:18,par:4,yards:476,avg:4.137,pm:0.137,eagles:0,birdies:53,pars:295,bogeys:81,dbl:16},
];

const FT_WRITEBACKS = [
  {id:'WB-2026-JDC-001',layer:'ANTI_PATTERN',confidence:'HIGH',current:'bomb_and_spray penalty applied at full weight regardless of course conditions',proposed:'Add soft/wet week modifier: reduce bomb_and_spray penalty 30–50% when FW% > 65% or course plays wet.',evidence:'Gotterup (bomb_and_spray → -2.67 SG) WON at -20. OTT 1st (+5.41). Meissner T6. Soft conditions neutered rough liability.'},
  {id:'WB-2026-JDC-002',layer:'VFD',confidence:'MEDIUM',current:'VFD weight held constant at venue-fit blend regardless of scoring profile',proposed:'At birdie-fest flat venues (Deere Run profile), reduce VFD weight 0.05 and transfer to NeutralSkill.',evidence:'Top-10 split across wide VFD range (-24.75 to +3.98). NeutralSkill SG correlated more cleanly with finish.'},
  {id:'WB-2026-JDC-003',layer:'DEBUT',confidence:'LOW',current:'B-class debut penalty: -1.75 SG applied uniformly',proposed:'Track B-class debut outcomes across 5+ events. Potential graduated penalty by data depth class.',evidence:'Brennan (debut B) finished T33, approach 13th (+4.44 SG). Over-penalized. Yellamaraju CUT — directionally correct.'},
  {id:'WB-2026-JDC-004',layer:'VHD',confidence:'HIGH',current:'VHD contributes at standard weight regardless of rounds history depth',proposed:'VHD rounds < 6 → widen variance band; cap VHD contribution at ±1.0 VTS pts.',evidence:'Koivun (Tier 1, VHD only 4 rounds, delta +0.024) missed cut at +1. Thin VHD = false confidence.'},
  {id:'WB-2026-JDC-005',layer:'NEUTRAL_SKILL',confidence:'MEDIUM',current:'ATG weight in NeutralSkill not venue-specific',proposed:'Increase ATG weight 5–10% at Deere Run profile venues (short par-4s, high wedge volume).',evidence:'Homa ATG 2nd (+3.82). Phillips ATG 1st (+4.56, T15). ATG consistently over-delivered vs. NeutralSkill projection.'},
  {id:'WB-2026-JDC-006',layer:'VHD',confidence:'HIGH',current:'No Tier 1 gate for thin VHD players',proposed:'Tier 1 gate: require VHD rounds ≥8 OR VHD >+1.0. Without it, Tier 1 is unsupported by venue signal.',evidence:'Koivun sole Tier 1 miss. Only 4 venue history rounds. VHD +0.024. Insufficient to support Tier 1.'},
];

const FT_MISS_LOG = [
  {player:'Jackson Koivun',tier:1,vts_rank:1,win_pct:'3.15%',top10_pct:'82.3%',finish:'CUT',miss_type:'CRITICAL MISS',layer:'VHD',wb:'WB-2026-JDC-004, 006'},
  {player:'Michael Thorbjornsen',tier:2,vts_rank:14,win_pct:'1.36%',top10_pct:'53.8%',finish:'CUT',miss_type:'CUT MISS',layer:'VARIANCE',wb:'—'},
  {player:'Denny McCarthy',tier:2,vts_rank:17,win_pct:'1.29%',top10_pct:'51.8%',finish:'CUT',miss_type:'CUT MISS',layer:'VARIANCE',wb:'—'},
  {player:'Michael Kim',tier:2,vts_rank:16,win_pct:'1.32%',top10_pct:'52.1%',finish:'CUT',miss_type:'CUT MISS',layer:'VARIANCE',wb:'—'},
  {player:'Max Greyserman',tier:2,vts_rank:23,win_pct:'1.24%',top10_pct:'49.6%',finish:'CUT',miss_type:'CUT MISS',layer:'VARIANCE',wb:'—'},
];

const FT_DNA_TRAITS = [
  {trait:'Par 5 Attack / Birdie-Fest Scoring',priority:'HIGH',evidence:'Hole 17: 205 birdies (most of any hole). Hole 14: 167 birdies (2nd most, par-4 playing as eagle hole). Holes 2, 10, 14, 17 generated 769 combined birdies.',status:'CONFIRMED'},
  {trait:'Putting Premium',priority:'HIGH',evidence:'Hodges putting 1st (+8.93). Meissner putting 2nd (+8.41). Gotterup putting 5th (+5.41). 3 of top-6 finishers had top-5 putting SG. Strongest DNA signal confirmed.',status:'CONFIRMED'},
  {trait:'OTT Importance',priority:'MODERATE',evidence:'Gotterup OTT 1st (+5.41). Suber OTT 7th (+3.10). But putting was more dominant. OTT important but secondary to putting in soft conditions.',status:'CONFIRMED'},
  {trait:'Approach Proximity',priority:'MODERATE',evidence:'Glover approach 1st (+9.05). Kohles 18th (+3.68). Homa 20th (+3.43). Approach leaders clustered in top 10. Trait confirmed.',status:'CONFIRMED'},
  {trait:'Bomb-and-Spray Risk',priority:'ANTI-PATTERN',evidence:'Gotterup won despite bomb_and_spray flag (-2.67 SG penalty). Meissner T6 despite flag. Soft conditions neutered rough liability penalty. Pattern needs conditions-conditioned modifier.',status:'CHALLENGED'},
];

const FT_SCORECARD = [
  {label:'Tier 1 Coverage Rate',value:'50%',detail:'1/2 T1 players: Griffin T21 (PARTIAL HIT). Koivun MISS (CUT).',status:'warn'},
  {label:'Tier 2 Hit+Partial Rate',value:'70%',detail:'28/40 T2 players: 6 HIT, 22 PARTIAL HIT, 9 MISS, 3 JUSTIFIED MISS.',status:'pass'},
  {label:'Top-10 Coverage',value:'54.5%',detail:'6 of 11 top-10 finishers were T1/T2. 5 Tier 3 players cracked top 10.',status:'warn'},
  {label:'Anti-Pattern Accuracy',value:'43%',detail:'3/7 key cases over-penalized. Soft conditions reduced rough liability impact.',status:'warn'},
  {label:'Cut Model',value:'PASS',detail:'Center 48% / steepness 0.07 appropriate. Koivun miss is VHD quality issue, not center parameter issue.',status:'pass'},
  {label:'Debut Accuracy (B-class)',value:'67%',detail:'2/3 directionally correct. Brennan T33 outperformed — over-penalized.',status:'pass'},
];

/* ── Build Final Tournament UI ── */
function buildFinalTournament() {
  buildFTLeaderboard();
  buildFTSGChart();
  buildFTScorecard();
  buildFTWinnerProfile();
  buildFTMissLog();
  buildFTDNA();
  buildFTWritebacks();
}

/* A: Leaderboard */
function buildFTLeaderboard() {
  const wrap = document.getElementById('ft-lb-table-wrap');
  if (!wrap) return;

  const allData = FT_LEADERBOARD;

  function posNum(p) {
    if (p === 'CUT' || p === 'WD') return 9999;
    return parseInt(p.replace('T','')) || 9999;
  }

  function renderTable(data) {
    const tierFilter = document.getElementById('ft-tier-filter')?.value || 'all';
    const search = (document.getElementById('ft-search')?.value || '').toLowerCase();
    const sortKey = document.getElementById('ft-sort')?.value || 'pos';

    let rows = data.filter(r => {
      if (tierFilter === 'cut') return r.pos === 'CUT';
      if (tierFilter !== 'all' && tierFilter !== 'cut') {
        if (r.pos === 'CUT') return false;
        if (String(r.tier) !== tierFilter) return false;
      }
      if (search && !r.player.toLowerCase().includes(search)) return false;
      return true;
    });

    if (sortKey === 'r4') rows.sort((a,b) => (a.r4||99)-(b.r4||99));
    else if (sortKey === 'sg') rows.sort((a,b) => (b.sg_total||(-999))-(a.sg_total||(-999)));
    else rows.sort((a,b) => posNum(a.pos)-posNum(b.pos));

    const tbody = rows.map(r => {
      const isCut = r.pos === 'CUT';
      const pn = posNum(r.pos);
      let rowCls = isCut ? 'ft-row-cut' : (pn === 1 ? 'ft-row-gold' : pn <= 2 ? 'ft-row-silver' : pn <= 5 ? 'ft-row-bronze' : '');
      const posCls = pn === 1 ? 'p1' : pn === 2 ? 'p2' : pn <= 5 ? 'p3' : '';
      const tierBadgeHtml = `<span class="tier-badge t${r.tier}">T${r.tier}</span>`;
      const scoreVal = parseFloat(r.total);
      const scoreCls = isNaN(scoreVal) ? 'ft-score even' : scoreVal < 0 ? 'ft-score under' : scoreVal > 0 ? 'ft-score over' : 'ft-score even';
      const sgHtml = r.sg_total != null ? `<span class="${r.sg_total >= 0 ? 'ft-sg-pos' : 'ft-sg-neg'}">${r.sg_total >= 0 ? '+' : ''}${r.sg_total.toFixed(2)}</span>` : '<span style="color:var(--muted)">N/A</span>';
      const madeCut = isCut ? '<span style="color:#fca5a5;font-size:.65rem;font-weight:700">CUT</span>' : '<span style="color:#86efac;font-size:.65rem;font-weight:700">✓</span>';
      return `<tr class="${rowCls}">
        <td class="ft-pos-cell ${posCls}">${r.pos}</td>
        <td>${tierBadgeHtml}</td>
        <td style="font-weight:600;color:var(--text)">${r.player}</td>
        <td><span class="${scoreCls}">${r.total}</span></td>
        <td class="ft-rd">${r.r1 ?? '—'}</td>
        <td class="ft-rd">${r.r2 ?? '—'}</td>
        <td class="ft-rd">${r.r3 ?? '—'}</td>
        <td class="ft-rd">${r.r4 ?? '—'}</td>
        <td style="font-size:.72rem;color:var(--muted)">${r.strokes ?? '—'}</td>
        <td class="ft-sg-cell">${sgHtml}</td>
        <td>${madeCut}</td>
      </tr>`;
    }).join('');

    wrap.innerHTML = `<table class="ft-table">
      <thead><tr>
        <th>Pos</th><th>Tier</th><th>Player</th><th>Total</th>
        <th>R1</th><th>R2</th><th>R3</th><th>R4</th>
        <th>Strokes</th><th>SG Total</th><th>Cut</th>
      </tr></thead>
      <tbody>${tbody || '<tr><td colspan="11" style="text-align:center;color:var(--muted);padding:1.5rem">No players match filter</td></tr>'}</tbody>
    </table>`;
  }

  renderTable(allData);
  document.getElementById('ft-tier-filter')?.addEventListener('change', () => renderTable(allData));
  document.getElementById('ft-sort')?.addEventListener('change', () => renderTable(allData));
  document.getElementById('ft-search')?.addEventListener('input', () => renderTable(allData));
}

/* B: SG Chart */
function buildFTSGChart() {
  const canvas = document.getElementById('ft-sg-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  const labels = FT_SG_TOP10.map(p => p.player);
  const datasets = [
    {label:'OTT',data:FT_SG_TOP10.map(p=>Math.max(0,p.ott)),backgroundColor:'#d97706'},
    {label:'Approach',data:FT_SG_TOP10.map(p=>Math.max(0,p.app)),backgroundColor:'#3b82f6'},
    {label:'ATG',data:FT_SG_TOP10.map(p=>Math.max(0,p.atg)),backgroundColor:'#8b5cf6'},
    {label:'Putting',data:FT_SG_TOP10.map(p=>Math.max(0,p.putt)),backgroundColor:'#16a34a'},
  ];

  new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#8896a8', font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: +${ctx.parsed.x.toFixed(2)}` } }
      },
      scales: {
        x: { stacked: true, grid: { color: '#2d3748' }, ticks: { color: '#8896a8' } },
        y: { stacked: true, grid: { color: '#2d3748' }, ticks: { color: '#e2e8f0', font: { size: 11 } } }
      }
    }
  });

  // Callout cards
  const callouts = document.getElementById('ft-sg-callouts');
  if (callouts) {
    callouts.innerHTML = [
      {val:'#1 OTT (+5.41)',label:"Winner's Off-the-Tee Rank"},
      {val:'#5 Putt (+5.40)',label:"Winner's Putting Rank"},
      {val:'54.5%',label:'Top-10 Coverage (T1+T2)'},
    ].map(c => `<div class="ft-sg-callout"><div class="ft-sg-callout-val">${c.val}</div><div class="ft-sg-callout-label">${c.label}</div></div>`).join('');
  }

  // Category leaders
  const leaders = document.getElementById('ft-sg-cat-leaders');
  if (leaders) {
    leaders.innerHTML = `<table class="ft-cat-leader-table">
      <thead><tr><th>Category</th><th>Leader</th><th>SG</th><th>Tier</th></tr></thead>
      <tbody>
        <tr><td>Off the Tee</td><td>Gotterup</td><td style="color:#86efac;font-weight:700">+5.41</td><td><span class="tier-badge t2">T2</span></td></tr>
        <tr><td>Approach</td><td>Glover</td><td style="color:#86efac;font-weight:700">+9.05</td><td><span class="tier-badge t3">T3</span></td></tr>
        <tr><td>ATG</td><td>Homa</td><td style="color:#86efac;font-weight:700">+3.82</td><td><span class="tier-badge t2">T2</span></td></tr>
        <tr><td>Putting</td><td>Hodges</td><td style="color:#86efac;font-weight:700">+8.93</td><td><span class="tier-badge t3">T3</span></td></tr>
      </tbody>
    </table>`;
  }
}

/* C: Model Scorecard */
function buildFTScorecard() {
  const el = document.getElementById('ft-scorecard-grid');
  if (!el) return;
  el.innerHTML = FT_SCORECARD.map(card => {
    const badgeCls = card.status === 'pass' ? 'ft-badge-pass' : card.status === 'warn' ? 'ft-badge-warn' : 'ft-badge-fail';
    const badgeLabel = card.status === 'pass' ? 'PASS' : card.status === 'warn' ? 'WARN' : 'FAIL';
    const valColor = card.status === 'pass' ? '#86efac' : card.status === 'warn' ? '#fde68a' : '#fca5a5';
    return `<div class="ft-scorecard-card">
      <div class="ft-scorecard-label">${card.label}</div>
      <div class="ft-scorecard-val" style="color:${valColor}">${card.value}</div>
      <div class="ft-scorecard-badge ${badgeCls}">${badgeLabel}</div>
      <div style="font-size:.67rem;color:var(--muted);margin-top:.5rem;line-height:1.4">${card.detail}</div>
    </div>`;
  }).join('');
}

/* D: Winner Profile */
function buildFTWinnerProfile() {
  const el = document.getElementById('ft-winner-profile');
  if (!el) return;
  const maxSG = 10;
  const sg = FT_SG_TOP10[0];
  const bars = [
    {label:'Off the Tee',val:sg.ott,rank:'1st',cls:'ott-bar'},
    {label:'Approach',val:sg.app,rank:'52nd',cls:'app-bar'},
    {label:'ATG',val:sg.atg,rank:'13th',cls:'atg-bar'},
    {label:'Putting',val:sg.putt,rank:'5th',cls:'putt-bar'},
  ].map(b => {
    const pct = Math.max(0, (b.val / maxSG) * 100).toFixed(0);
    const valStr = (b.val >= 0 ? '+' : '') + b.val.toFixed(2);
    return `<div class="ft-sg-bar-row">
      <span class="ft-sg-bar-label">${b.label}</span>
      <div class="ft-sg-bar-bg"><div class="ft-sg-bar-fill ${b.cls}" style="width:${pct}%"></div></div>
      <span class="ft-sg-bar-val">${valStr}</span>
      <span class="ft-sg-bar-rank">(${b.rank})</span>
    </div>`;
  }).join('');

  el.innerHTML = `<div class="ft-winner-card">
    <div class="ft-winner-left">
      <div style="font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);margin-bottom:.4rem">CHAMPION — 2026 John Deere Classic</div>
      <div class="ft-winner-name">Chris Gotterup</div>
      <div class="ft-winner-score">-20</div>
      <div class="ft-winner-sub">264 total strokes | TPC Deere Run, Silvis IL | Rounds: 66-68-68-62</div>
      <div class="ft-winner-sg-bars" style="margin-top:1rem">${bars}</div>
    </div>
    <div class="ft-winner-right">
      <div class="ft-winner-proj-box">
        <div class="ft-proj-title">Pre-Tournament Model Projection</div>
        <div style="font-size:.72rem;color:var(--muted);margin-bottom:.55rem">Tier 2 · Rank #6 · VTS 75.5</div>
        <div class="ft-proj-pills">
          <div class="ft-proj-pill"><div class="ft-proj-pill-val" style="color:var(--gold)">1.70%</div><div class="ft-proj-pill-label">Win%</div></div>
          <div class="ft-proj-pill"><div class="ft-proj-pill-val" style="color:#60a5fa">59.6%</div><div class="ft-proj-pill-label">Top 10%</div></div>
          <div class="ft-proj-pill"><div class="ft-proj-pill-val" style="color:#86efac">78.5%</div><div class="ft-proj-pill-label">Cut%</div></div>
        </div>
      </div>
      <div class="ft-ap-alert">
        <div class="ft-ap-alert-title">Anti-Pattern Alert</div>
        <div class="ft-ap-alert-body">
          <b>bomb_and_spray + rough_approach_liab</b> flags applied → <b>-2.67 SG total penalty</b><br>
          Actual OTT: <b>+5.41 (1st in field)</b><br>
          Soft/wet conditions neutered rough liability. Penalty over-applied.<br>
          → <span style="color:#fde68a;font-weight:600">Write-back: WB-2026-JDC-001 triggered</span>
        </div>
      </div>
      <div>
        <span class="ft-verdict-badge">LOW-PROB HIT</span>
        <span class="ft-verdict-wb">WRITE-BACK TRIGGERED</span>
      </div>
      <div style="font-size:.68rem;color:var(--muted);margin-top:.55rem;line-height:1.4">
        Model correctly identified Gotterup in contention window (Top10% 59.6%). Win at 1.70% projected probability is within model variance. The VFD (-24.75) and bomb_and_spray penalty interaction with soft conditions is the systematic write-back finding.
      </div>
    </div>
  </div>`;
}

/* E: Miss Log */
function buildFTMissLog() {
  const el = document.getElementById('ft-miss-log-wrap');
  if (!el) return;
  const rows = FT_MISS_LOG.map(r => `<tr>
    <td style="font-weight:600;color:var(--text)">${r.player}</td>
    <td><span class="tier-badge t${r.tier}">T${r.tier}</span></td>
    <td style="color:var(--muted);font-size:.72rem">#${r.vts_rank}</td>
    <td style="color:var(--gold);font-size:.72rem">${r.win_pct}</td>
    <td style="color:#60a5fa;font-size:.72rem">${r.top10_pct}</td>
    <td style="font-weight:700;color:#fca5a5">${r.finish}</td>
    <td style="font-size:.68rem;color:#fca5a5">${r.miss_type}</td>
    <td><span class="ft-layer-badge">${r.layer}</span></td>
    <td style="font-size:.65rem;color:var(--muted)">${r.wb}</td>
  </tr>`).join('');
  el.innerHTML = `<table class="ft-miss-table">
    <thead><tr>
      <th>Player</th><th>Tier</th><th>VTS Rank</th><th>Proj Win%</th><th>Proj Top10%</th>
      <th>Actual Finish</th><th>Miss Type</th><th>Layer</th><th>Write-Back</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

/* F: Course DNA */
function buildFTDNA() {
  const traitsEl = document.getElementById('ft-dna-traits');
  if (traitsEl) {
    traitsEl.innerHTML = `<div class="ft-sub-title">DNA Trait Confirmation</div>` + FT_DNA_TRAITS.map(t => {
      const cls = t.status === 'CONFIRMED' ? 'ft-dna-confirm' : t.status === 'CHALLENGED' ? 'ft-dna-challenge' : 'ft-dna-partial';
      const icon = t.status === 'CONFIRMED' ? '✓ CONFIRMED' : t.status === 'CHALLENGED' ? '✗ CHALLENGED' : '⚠ PARTIAL';
      return `<div class="ft-dna-row">
        <div>
          <div class="ft-dna-trait">${t.trait} <span style="font-size:.62rem;color:var(--muted)">[${t.priority}]</span></div>
          <div class="ft-dna-evidence">${t.evidence}</div>
        </div>
        <span class="ft-dna-badge ${cls}" style="white-space:nowrap;flex-shrink:0">${icon}</span>
      </div>`;
    }).join('');
  }

  // Hole chart
  const canvas = document.getElementById('ft-hole-chart');
  if (canvas && typeof Chart !== 'undefined') {
    const par5Holes = [2,10,17];
    const bgColors = FT_COURSE_STATS.map(h => par5Holes.includes(h.hole) ? '#16a34a' : h.pm < 0 ? '#3b82f6' : '#ef4444');
    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: FT_COURSE_STATS.map(h => `H${h.hole}`),
        datasets: [{
          label: 'Birdies',
          data: FT_COURSE_STATS.map(h => h.birdies),
          backgroundColor: bgColors,
          borderRadius: 3,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: {
            label: (ctx) => {
              const h = FT_COURSE_STATS[ctx.dataIndex];
              return [`Birdies: ${h.birdies}`, `Avg: ${h.avg}`, `Par ${h.par} | ${h.yards}y`, `${h.pm > 0 ? '+' : ''}${h.pm} vs par`];
            }
          }}
        },
        scales: {
          x: { grid: { color: '#2d3748' }, ticks: { color: '#8896a8', font: { size: 10 } } },
          y: { grid: { color: '#2d3748' }, ticks: { color: '#8896a8' }, title: { display: true, text: 'Birdies', color: '#8896a8', font: { size: 11 } } }
        }
      }
    });
  }
}

/* G: Write-back recommendations */
function buildFTWritebacks() {
  const el = document.getElementById('ft-wb-grid');
  if (!el) return;
  el.innerHTML = FT_WRITEBACKS.map(wb => {
    const confCls = wb.confidence.toLowerCase();
    return `<div class="ft-wb-card">
      <div class="ft-wb-flag">
        <span class="ft-wb-id">${wb.id}</span>
        <span class="ft-wb-layer">${wb.layer}</span>
        <span class="ft-wb-conf ${confCls}">${wb.confidence}</span>
      </div>
      <div class="ft-wb-current"><b style="color:var(--muted)">Current:</b> ${wb.current}</div>
      <div class="ft-wb-proposed">${wb.proposed}</div>
      <div class="ft-wb-evidence"><b>Evidence:</b> ${wb.evidence}</div>
    </div>`;
  }).join('');
}

/* ── Init page tabs on load ── */
document.addEventListener('DOMContentLoaded', initPageTabs);

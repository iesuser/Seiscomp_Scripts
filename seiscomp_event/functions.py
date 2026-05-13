# -*- coding: utf-8 -*-
import  pymysql, math, os, datetime

# seiscomp-ის მონაცემთა ბაზასთან დასაკავშირებელი პარამეტრები
hostname = "127.0.0.1"
sc_username = "sysop"
sc_password = "sysop"
sc_databasename = "seiscomp"

# ies_borders ბაზასთან დასაკავშირებელი პარამეტრები
ies_borders_username = 'ies_borders'
ies_borders_password = 'cJ03&57v6cqf'
ies_borders_databasename = 'ies_borders'


# log ფაილის სახელი
log_filename = "LOG"
# სკრიპტი ბეჭდავდეს თუ არა ტერმინალში
printing = True
# სკრიპტი წერდეს თუ არა log ფაილში
write_in_log = True
# გავიგოთ მისამართი საიდანაც გაეშვა ies_time_check.py სკრიპტი
script_path = os.path.dirname(os.path.realpath(__file__))


def print_and_log(message, empty_line=False):
    message = str(message)
    #message = str(message.encode('utf-8'))
    try:
        log_file_path = script_path + "/" + log_filename
        pid = os.getpid()
        if printing is True:
            print("[" + datetime.datetime.now().strftime('%Y-%m-%d %T') + "] [" + str(pid) + "] " + message)
        if write_in_log is True:
            with open(log_file_path, "a") as log_file:
                if not empty_line:
                    log_file.write("[" + datetime.datetime.now().strftime('%Y-%m-%d %T') + "] [" + str(pid) + "] " + message + "\n")
                else:
                    log_file.write("\n")
    except Exception as ex:
        with open(log_file_path, "a") as log_file:
            message = "შეცდომა print_and_log() ფუნქციაში: " + str(ex)
            log_file.write("[" + datetime.datetime.now().strftime('%Y-%m-%d %T') + "] [" + str(pid) + "] " + message + "\n")





def connect_db(hostname, username, password, databasename):
    try:
        db = pymysql.connect(host=hostname, user=username, password=password, database=databasename, charset='utf8')
    except Exception as e:
        print_and_log(str(e))

    cursor = db.cursor()
    cursor.execute('SET NAMES utf8;')
    cursor.execute('SET CHARACTER SET utf8;')
    cursor.execute('SET character_set_connection=utf8;')

    return db, cursor 


ies_db, ies_cursor = connect_db(hostname, ies_borders_username, ies_borders_password, ies_borders_databasename)

def GetParamiter(public_event_id):
    # seiscomp-ის მონაცემთა ბაზასთან დაკავშირება
    
    sc_db, sc_cursor = connect_db(hostname, sc_username, sc_password, sc_databasename)

    try:
        sql = """SELECT O.longitude_value, O.latitude_value, O.depth_value, O.evaluationMode, O.time_value, O._oid FROM `PublicObject` AS P1
                LEFT JOIN OriginReference AS OR1 ON OR1._parent_oid = P1._oid
                LEFT JOIN PublicObject AS P2 ON P2.publicID = OR1.originID
                LEFT JOIN Origin AS O ON O._oid = P2._oid
                WHERE P1.publicID = '%s'
                ORDER BY O.creationInfo_creationTime DESC
                LIMIT 1 """ % public_event_id

        sc_cursor.execute(sql)
        results = sc_cursor.fetchall()
        if sc_cursor.rowcount != 0:
            for row in results:
                Lon = row[0]
                Lat = row[1]
                depth = row[2]
                evMode = row[3]
                time = row[4]
                oid = row[5]
            sql = "SELECT type,magnitude_value FROM Magnitude WHERE _parent_oid='%s'" % oid
            sc_cursor.execute(sql)
            results = sc_cursor.fetchall()

            # ბაზის და კურსორის დახურვა
            sc_cursor.close()
            sc_db.close()
            # magnitudis tipebis wakitxva seiscomp-is bazidan
            if sc_cursor.rowcount != 0:
                magnitudes = {}
                for row in results:
                    # ივსება Origin - ის მაგნიტუდების ლექსიკონი
                    magnitudes.update( { row[0] : float(row[1]) } )
                return str(time), float(Lat), float(Lon), float(depth), str(evMode), magnitudes
            else:
                print_and_log("მონაცემთა ბაზაში არ იძებნება მაგნიტუდების ჩანაწერი შემდეგი originID = '%s' - ით" % oid)
                return "0"
        else:
            print_and_log("მონაცემთა ბაზაში არ იძებნება ჩანაწერი(origin) შემდეგი EventID = '%s' - ით" % public_event_id)
            sc_cursor.close()
            sc_db.close()
            return "0"
    except pymysql.Error as e:
        print_and_log("MySQL Error %d:  %s" % ( e.args[0], e.args[1] ))
        return "0"
    return "0"



def choose_prefered_magnitude(magnitudes):
    for mtype, mvalue in magnitudes.items():
        if mtype.lower() == "ml":
            return mtype, mvalue
    for mtype, mvalue in magnitudes.items():
        if mtype.lower() == "m":
            return mtype, mvalue
    for mtype, mvalue in magnitudes.items():
        return mtype, mvalue

    



def calculate_hypocentral_distance(depth, epicentral_distance):
    hypocentral_distance = float(depth) ** 2 + float(epicentral_distance) ** 2
    return math.sqrt(hypocentral_distance + 9)

def calculate_acceleration_with_hypocenter(magnitude, corrected_hypocentral_distance):
    first_formule = -4.4983 + 1.3209 * magnitude - 0.0656 * (magnitude**2) - 0.0041 * \
    corrected_hypocentral_distance - 0.5229 * math.log10( corrected_hypocentral_distance**2)
    acceleration = 10**first_formule
    return acceleration

def calculate_acceleration(magnitude, epicentral_distance, depth):
    return calculate_acceleration_with_hypocenter(magnitude, calculate_hypocentral_distance(depth, epicentral_distance))


def inBorder(lat,lon,border):
    x=lat 
    y=lon
    poly = []
    inside = False
    sql = "SELECT latitude,longitude FROM %s" % border
    ies_cursor.execute(sql)
    results = ies_cursor.fetchall()
    for row in results:
        polytmp = [row[0],row[1]]
        poly.append(polytmp)
    n = len(poly)
    p1x, p1y = poly[0]
    count = 0
    for i in range(n+1):    
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x   
                    if p1x == p2x or x <=xinters:
                        inside = not inside
                        count+=1    
        p1x,p1y = p2x,p2y
    #print "*****"+str(n)+" "+border+" "+str(borderMinDistance(x,y,border))+" "+str(inside)+" "+str(count)
    return inside

def finddist(lat1, lat2, lon1, lon2):
    
    start_long = math.radians(lon1)
    start_latt = math.radians(lat1)
    end_long = math.radians(lon2)
    end_latt = math.radians(lat2)
    d_latt = end_latt - start_latt
    d_long = end_long - start_long
    a = math.sin(d_latt/2)**2 + math.cos(start_latt) * math.cos(end_latt) * math.sin(d_long/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c*6371

def finddegee(lat1, lat2, lon1, lon2): #pirveli unda iyos qalqis da mere miwisdzvris oordinatebi
    
    dlat=lat2-lat1   #latitude differance
    dlon=lon2-lon1   #longitude differance
    if dlat >= 0 and dlon==0:
        degree=90
    elif dlat <= 0 and dlon ==0:
        degree = 270
    elif dlat >= 0 and dlon>0 :
        degree = math.degrees(math.atan((lat2-lat1)/(lon2-lon1)))
    elif dlat >= 0 and dlon < 0 :
        degree = 180 + math.degrees(math.atan((lat2-lat1)/(lon2-lon1)))
    elif dlat <= 0 and dlon < 0 :
        degree = 180 + math.degrees(math.atan((lat2-lat1)/(lon2-lon1)))
    elif dlat <= 0 and dlon > 0 :
        degree = 360 + math.degrees(math.atan((lat2-lat1)/(lon2-lon1)))
        #print "%.2f " % degree +"%.1f" % (6371 * c)
    
    #return str(int(degree))
    if degree < 23 or degree >= 338:
        return "აღმოსავლეთით"
    if degree >= 23 and degree < 68:
        return "ჩრდილო-აღმოსავლეთით"
    if degree >= 68 and degree < 113:
        return "ჩრდილოეთით"
    if degree >= 113 and degree < 158:
        return "ჩრდილო-დასავლეთით"
    if degree >= 158 and degree < 203:
        return "დასავლეთით"
    if degree >= 203 and degree < 248:
        return "სამხრეთ-დასავლეთით"
    if degree >= 248 and degree < 293:
        return "სამხრეთით"
    if degree >= 293 and degree < 338:
        return "სამხრეთ-აღმოსავლეთით"
    return " "


def findNCity(lat, lon):  # aq iqneba shesacveleli
    sql = "SELECT latitude,longitude,name_ge,status_ge,radius FROM cities_caucasus WHERE status_en != 'tbilisi' "
    try:
        ies_cursor.execute(sql)
        results = ies_cursor.fetchall()
        distance=5000
        for row in results:         
            citylat = row[0]
            citylon = row[1]
            name = row[2]
            status = row[3]
            radius = int(row[4])
            tempdistance=finddist(citylat, lat, citylon, lon)-radius-1
            if tempdistance > 0:
                if distance > tempdistance:
                    distance = tempdistance
                    message = " "+status+" "+name
                    message = message +", "+ finddegee(citylat, lat, citylon, lon) +":"+ str(int(distance))+"კმ."
            else:
                message = status+" "+name+"."
                return message  
    except:
        print("Error: unable to fecth data")
        exit(1)
    message=message+findNSettlement(lat,lon)
    return message

def findNSettlement(lat,lon):
    sql = "SELECT latitude,longitude,name_ge,status_ge FROM settlements_georgia"
    try:
        ies_cursor.execute(sql)
        results = ies_cursor.fetchall()
        distance=5000
        for row in results:
            #print str(row[0])+" "+str(row[1])+" "+str(row[2])+" "+str(row[3])+" "
            citylat = row[0]
            citylon = row[1]
            name = row[2]
            status = row[3]
            tempdistance=finddist(citylat, lat, citylon, lon)-1
            if distance > tempdistance:
                distance = tempdistance
                message = " "+status+" "+name
                message = message +":"+str(int(distance))+"კმ."
    except:
        print("Error: unable to fecth data")
        exit(1)
    return message
                
def borderMinDistance(lat,lon,border):
    sql = "SELECT latitude,longitude FROM %s" % border
    ies_cursor.execute(sql)
    results = ies_cursor.fetchall()
    min_distance=5000
    for row in results:
        temp_distance=finddist(lat, row[0], lon, row[1])
        if temp_distance < min_distance:
            min_distance = temp_distance
    return int(min_distance)

def findCountry(lat,lon,bor_min_dis):
    if inBorder(lat,lon,"border_turkey"):
        if inBorder(lat,lon,"subborder_turkey_taoklarjeti"): 
            return "ტაო-კლარჯეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
        return "თურქეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
    else:
        if inBorder(lat,lon,"border_arminia"): 
            return "სომხეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
        else:
            if inBorder(lat,lon,"border_azerbaijan"):
                return "აზერბაიჯანი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
            else:
                if inBorder(lat,lon,"border_russia"):
                    if inBorder(lat,lon,"subborder_russia_adigea"): 
                        return "რუსეთი, ადიღეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                    else:
                        if inBorder(lat,lon,"subborder_russia_chechnia"): 
                            return "რუსეთი, ჩეჩნეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                        else:
                            if inBorder(lat,lon,"subborder_russia_dagestan"): 
                                return "რუსეთი, დაღესტანი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                            else:
                                if inBorder(lat,lon,"subborder_russia_ingusheti"): 
                                    return "რუსეთი, ინგუშეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                                else:
                                    if inBorder(lat,lon,"subborder_russia_kabardino_balkaria"): 
                                        return "რუსეთი, ყაბარდო-ბალკანეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                                    else:
                                        if inBorder(lat,lon,"subborder_russia_karachai"): 
                                            return "რუსეთი, ყარაჩაი-ჩერქეზეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                                        else:
                                            if inBorder(lat,lon,"subborder_russia_krasnodar"): 
                                                return "რუსეთი, კრასნოდარი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                                            else:
                                                if inBorder(lat,lon,"subborder_russia_north_oseti"): 
                                                    return "რუსეთი, ჩრიდლოეთ ოსეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                        return "რუსეთი, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."
                else:
                    if inBorder(lat,lon,"border_black_sea"):
                        return "შავი ზღვა, საქართველოს სანაპირო ზოლიდან "+str(bor_min_dis)+"კმ."
                    else: return "საზღვარგარეთ, საქართველოს საზღვრიდან "+str(bor_min_dis)+"კმ."

def findtbilisi(orgLat,orgLon,distance):
    if inBorder(orgLat,orgLon,"subborder_tbilisi"):
        if inBorder(orgLat,orgLon,"subborder_tbilisi_didgori"):
            return "თბილისი, დიდგორის რაიონი."
        else:
            if inBorder(orgLat,orgLon,"subborder_tbilisi_didube_chughureti"):
                return "თბილისი, დიდუბე-ჩუღურეთის რაიონი."
            else:
                if inBorder(orgLat,orgLon,"subborder_tbilisi_gldani_nadzaladevi"):
                    return "თბილისი, გლდანი-ნაძალადევის რაიონი"
                else:
                    if inBorder(orgLat,orgLon,"subborder_tbilisi_isani_samgori"):
                        return "თბილისი, ისანი-სამგორის რაიონი."
                    else:
                        if inBorder(orgLat,orgLon,"subborder_tbilisi_old_tbilisi"):
                            return "თბილისი, ძველი თბილისის რაიონი."
                        else:
                            if inBorder(orgLat,orgLon,"subborder_tbilisi_vake_saburtalo"):
                                return "თბილისი, ვაკე-საბურთალოს რაიონი."
                            else:
                                return "თბილისი."
    else:
        if distance < 3:
            message = " თბილისის საზღვარი."
        else:
            message = " თბილისიდან "+str(distance)+"კმ."
        message = message + findNCity(orgLat,orgLon)
        return message
#db.close()

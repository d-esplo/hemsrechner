import pgeocode
import pandas

nomi = pgeocode.Nominatim('de') 
a = nomi.query_postal_code("40599")

print(a['latitude'], a['longitude'])
print(a)

latitude = a['latitude']
longitude = a['longitude']
print(longitude)
print(latitude)


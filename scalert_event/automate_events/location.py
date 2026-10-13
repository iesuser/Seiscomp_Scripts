"""Spatial queries and Georgian location descriptions for an epicentre.

The text fragments built here are concatenated into the notification, e.g.
"საქართველო." + " ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ." + " სოფელი ბეჟანო:0კმ."
Their exact spacing and punctuation match the historic alert messages, so a
fragment may start with a space and the next one may rely on it.
"""

from dataclasses import dataclass, field

from . import geo
from .borders_db import BordersRepository

# Polygon table names in the borders database used directly by the rules.
GEORGIA = "border_georgia"
TBILISI = "subborder_tbilisi"
BLACK_SEA = "border_black_sea"

# Below this distance (km) an epicentre is described as "on the Tbilisi border".
_TBILISI_BORDER_KM = 3


@dataclass(frozen=True)
class Region:
    """A named area backed by a polygon table.

    Attributes:
        table: Polygon table in the borders database.
        label_ge: Georgian name used in the notification.
        subregions: More specific areas inside this one; when the epicentre is in
            one of them, its label replaces the parent's.
    """

    table: str
    label_ge: str
    subregions: tuple["Region", ...] = field(default=())


# Checked in order; the first matching country wins, then its first matching subregion.
NEIGHBOUR_COUNTRIES = (
    Region(
        "border_turkey",
        "თურქეთი",
        (Region("subborder_turkey_taoklarjeti", "ტაო-კლარჯეთი"),),
    ),
    Region("border_arminia", "სომხეთი"),
    Region("border_azerbaijan", "აზერბაიჯანი"),
    Region(
        "border_russia",
        "რუსეთი",
        (
            Region("subborder_russia_adigea", "რუსეთი, ადიღეთი"),
            Region("subborder_russia_chechnia", "რუსეთი, ჩეჩნეთი"),
            Region("subborder_russia_dagestan", "რუსეთი, დაღესტანი"),
            Region("subborder_russia_ingusheti", "რუსეთი, ინგუშეთი"),
            Region("subborder_russia_kabardino_balkaria", "რუსეთი, ყაბარდო-ბალკანეთი"),
            Region("subborder_russia_karachai", "რუსეთი, ყარაჩაი-ჩერქეზეთი"),
            Region("subborder_russia_krasnodar", "რუსეთი, კრასნოდარი"),
            Region("subborder_russia_north_oseti", "რუსეთი, ჩრიდლოეთ ოსეთი"),
        ),
    ),
)

# Checked in order; an epicentre in Tbilisi but in none of these is just "თბილისი.".
TBILISI_DISTRICTS = (
    Region("subborder_tbilisi_didgori", "თბილისი, დიდგორის რაიონი."),
    Region("subborder_tbilisi_didube_chughureti", "თბილისი, დიდუბე-ჩუღურეთის რაიონი."),
    Region("subborder_tbilisi_gldani_nadzaladevi", "თბილისი, გლდანი-ნაძალადევის რაიონი"),
    Region("subborder_tbilisi_isani_samgori", "თბილისი, ისანი-სამგორის რაიონი."),
    Region("subborder_tbilisi_old_tbilisi", "თბილისი, ძველი თბილისის რაიონი."),
    Region("subborder_tbilisi_vake_saburtalo", "თბილისი, ვაკე-საბურთალოს რაიონი."),
)


class LocationService:
    """Answers "where is this epicentre?" using the borders repository.

    Rules depend on this class's public methods only, so tests can replace it
    with a fake that returns fixed answers.
    """

    def __init__(self, repository: BordersRepository):
        self._repository = repository

    def is_inside(self, lat: float, lon: float, table: str) -> bool:
        """True if the point lies inside the polygon stored in `table`."""
        return geo.point_in_polygon(lat, lon, self._repository.polygon(table))

    def distance_to_border_km(self, lat: float, lon: float, table: str) -> int:
        """Shortest distance to the region's border vertices, truncated to whole km.

        Measured to the polygon's vertices, not its edges, which is accurate
        enough because the stored borders are densely sampled.
        """
        return int(geo.min_distance_km(lat, lon, self._repository.polygon(table)))

    def describe_nearest_city(self, lat: float, lon: float) -> str:
        """Nearest city with direction and distance, followed by the nearest settlement.

        Distance is measured from the edge of the city (its centre minus its
        radius), minus a further 1 km kept from the historic alert texts.
        If the epicentre lies within a city, only that city is returned.
        Example: " ქალაქი ახალქალაქი, ჩრდილო-აღმოსავლეთით:21კმ. სოფელი ბეჟანო:0კმ."
        """
        best_distance = float("inf")
        text = ""
        for city in self._repository.cities():
            distance = geo.haversine_km(city.latitude, city.longitude, lat, lon) - city.radius_km - 1
            if distance <= 0:
                return f"{city.status_ge} {city.name_ge}."
            if distance < best_distance:
                best_distance = distance
                # Direction of the epicentre as seen from the city.
                direction = geo.compass_direction_ge(city.latitude, city.longitude, lat, lon)
                text = f" {city.status_ge} {city.name_ge}, {direction}:{int(distance)}კმ."
        return text + self._describe_nearest_settlement(lat, lon)

    def describe_neighbour_country(self, lat: float, lon: float, border_distance_km: int) -> str:
        """Country (and region, when known) of an epicentre outside Georgia.

        Example: "ტაო-კლარჯეთი, საქართველოს საზღვრიდან 85კმ."
        """
        for country in NEIGHBOUR_COUNTRIES:
            if self.is_inside(lat, lon, country.table):
                label = self._first_matching_label(lat, lon, country.subregions) or country.label_ge
                return f"{label}, საქართველოს საზღვრიდან {border_distance_km}კმ."
        if self.is_inside(lat, lon, BLACK_SEA):
            return f"შავი ზღვა, საქართველოს სანაპირო ზოლიდან {border_distance_km}კმ."
        return f"საზღვარგარეთ, საქართველოს საზღვრიდან {border_distance_km}კმ."

    def describe_relative_to_tbilisi(self, lat: float, lon: float, distance_km: int) -> str:
        """Tbilisi district when inside the city, otherwise distance to it plus nearest city.

        `distance_km` is the distance to the Tbilisi border; it is ignored when
        the epicentre is inside Tbilisi.
        """
        if self.is_inside(lat, lon, TBILISI):
            return self._first_matching_label(lat, lon, TBILISI_DISTRICTS) or "თბილისი."

        if distance_km < _TBILISI_BORDER_KM:
            prefix = " თბილისის საზღვარი."
        else:
            prefix = f" თბილისიდან {distance_km}კმ."
        return prefix + self.describe_nearest_city(lat, lon)

    def _describe_nearest_settlement(self, lat: float, lon: float) -> str:
        """Nearest Georgian settlement, e.g. " სოფელი ბეჟანო:0კმ.", or "" if there are none.

        The 1 km offset matches the historic alert texts; very close settlements
        can therefore show 0 km or, on the epicentre itself, -1 km.
        """
        best_distance = float("inf")
        text = ""
        for settlement in self._repository.settlements():
            distance = geo.haversine_km(settlement.latitude, settlement.longitude, lat, lon) - 1
            if distance < best_distance:
                best_distance = distance
                text = f" {settlement.status_ge} {settlement.name_ge}:{int(distance)}კმ."
        return text

    def _first_matching_label(self, lat: float, lon: float, regions: tuple[Region, ...]) -> str | None:
        """Label of the first region containing the point, or None."""
        for region in regions:
            if self.is_inside(lat, lon, region.table):
                return region.label_ge
        return None

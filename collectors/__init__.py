# Collectors package
from collectors.disease_sh import DiseaseSHCollector
from collectors.who_gho import WHOGHOCollector
from collectors.cdc_open import CDCOpenCollector
from collectors.cdc_fluview import CDCFluViewCollector
from collectors.promed import ProMEDCollector
from collectors.healthmap import HealthMapCollector
from collectors.ihme_ghdx import IHMEGHDxCollector
from collectors.ecdc import ECDCCollector
from collectors.uk_gov import UKGovCollector

ALL_COLLECTORS = [
    DiseaseSHCollector,
    WHOGHOCollector,
    CDCOpenCollector,
    CDCFluViewCollector,
    ProMEDCollector,
    HealthMapCollector,
    IHMEGHDxCollector,
    ECDCCollector,
    UKGovCollector,
]

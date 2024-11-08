import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia

Gaia.ROW_LIMIT = 999999

def gaia_query(ra, dec, radius = 1):
    job = Gaia.launch_job_async("select "
                      "source.source_id, source.ra, source.dec, "
                      "source.parallax, source.parallax_error, "
                      "source.phot_g_mean_mag, source.phot_bp_mean_mag, source.phot_rp_mean_mag, "
                      "source.teff_gspphot "
                      "from gaiadr3.gaia_source as source "
                      f"where 1=contains(point('ICRS', source.ra, source.dec), circle('ICRS', {ra}, {dec}, {radius / 3600})) "
    )
    
    r = job.get_results()
    return r

if __name__ == "__main__":
    # 
    from astropy.coordinates import FK5
    
    ra, dec = 174.50347999226292, -63.37449056169426
    
    c = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg))
    r = gaia_query(c.ra.deg, c.dec.deg, 2)
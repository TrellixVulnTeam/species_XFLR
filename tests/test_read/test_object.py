import os
import shutil

import pytest
import numpy as np

import species
from species.util import test_util


class TestObject:
    def setup_class(self):
        self.limit = 1e-8
        self.test_path = os.path.dirname(__file__) + "/"

    def teardown_class(self):
        os.remove("species_database.hdf5")
        os.remove("species_config.ini")
        shutil.rmtree("data/")

    def test_species_init(self):
        test_util.create_config("./")
        species.SpeciesInit()

    def test_read_object(self):
        database = species.Database()

        with pytest.warns(UserWarning):
            database.add_companion(name="beta Pic b")

        read_object = species.ReadObject("beta Pic b")
        assert read_object.object_name == "beta Pic b"

        with pytest.raises(ValueError) as error:
            species.ReadObject("wrong name")

        assert (
            str(error.value)
            == "The object 'wrong name' is not present in the database."
        )

    def test_get_photometry(self):
        read_object = species.ReadObject("beta Pic b")
        photometry = read_object.get_photometry("Paranal/NACO.Lp")

        assert isinstance(photometry, np.ndarray)

        assert photometry[0] == pytest.approx(11.3, rel=self.limit, abs=0.0)
        assert photometry[1] == pytest.approx(0.06, rel=self.limit, abs=0.0)
        assert photometry[2] == pytest.approx(
            1.5898815856603153e-15, rel=self.limit, abs=0.0
        )
        assert photometry[3] == pytest.approx(
            8.790482938961674e-17, rel=self.limit, abs=0.0
        )

    def test_get_parallax(self):
        read_object = species.ReadObject("beta Pic b")
        parallax = read_object.get_parallax()

        assert parallax == (51.44, 0.11999999731779099)

    def test_get_distance(self):
        read_object = species.ReadObject("beta Pic b")
        distance = read_object.get_distance()

        assert distance == (19.440124416796266, 0.04535045826554729)

    def test_get_absmag(self):
        read_object = species.ReadObject("beta Pic b")
        abs_mag = read_object.get_absmag("Paranal/NACO.Lp")

        assert abs_mag[0] == pytest.approx(9.85650479958083, rel=self.limit, abs=0.0)
        assert abs_mag[1] == pytest.approx(0.06021346211401161, rel=self.limit, abs=0.0)

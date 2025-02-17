"""
Module for isochrone data from evolutionary models.
"""

import os
import tarfile
import urllib.request

import h5py
import numpy as np

from species.core import constants


def add_manual(database, tag, file_name):
    """
    Function for adding any of the isochrones from
    https://phoenix.ens-lyon.fr/Grids/ or
    https://perso.ens-lyon.fr/isabelle.baraffe/ to
    the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    tag : str
        Tag name in the database.
    file_name : str
        Filename with the isochrones data.

    Returns
    -------
    NoneType
        None
    """

    # Read in all the data, ignoring empty lines or lines with "---"

    data = []

    check_baraffe = False
    baraffe_continue = False

    with open(file_name, encoding="utf-8") as open_file:
        for i, line in enumerate(open_file):
            if "BHAC15" in line:
                check_baraffe = True
                continue

            if not baraffe_continue:
                if "(Gyr)" in line:
                    baraffe_continue = True
                else:
                    continue

            if line[0] == "!":
                line = line[1:]

            elif line[:2] == " !":
                line = line[2:]

            if "---" in line or line == "\n":
                continue

            data.append(list(filter(None, line.rstrip().split(" "))))

    isochrones = []

    for line in data:
        if "(Gyr)" in line:
            age = line[-1]

        elif "lg(g)" in line:
            # Isochrones from Phoenix website
            header = ["M/Ms", "Teff(K)"] + line[1:]

        elif "M/Ms" in line:
            # Isochrones from Baraffe et al. (2015)
            header = line.copy()

        else:
            line.insert(0, age)
            isochrones.append(line)

    header = np.asarray(header, dtype=str)
    isochrones = np.asarray(isochrones, dtype=float)

    isochrones[:, 0] *= 1e3  # (Myr)
    isochrones[:, 1] *= constants.M_SUN / constants.M_JUP  # (Mjup)

    index_sort = np.argsort(isochrones[:, 0])
    isochrones = isochrones[index_sort, :]

    print(f"Adding isochrones: {tag}...", end="", flush=True)

    if check_baraffe:
        filters = header[6:]
    else:
        filters = header[7:]

    dtype = h5py.string_dtype(encoding='utf-8', length=None)

    dset = database.create_dataset(
        f"isochrones/{tag}/filters", (np.size(filters),), dtype=dtype
    )

    dset[...] = filters

    database.create_dataset(f"isochrones/{tag}/magnitudes", data=isochrones[:, 8:])

    dset = database.create_dataset(
        f"isochrones/{tag}/evolution", data=isochrones[:, 0:8]
    )

    dset.attrs["model"] = "manual"

    print(" [DONE]")
    print(f"Database tag: {tag}")


def add_marleau(database, tag, file_name):
    """
    Function for adding the Marleau et al. isochrone data
    to the database. The isochrone data can be requested
    from Gabriel Marleau.

    https://ui.adsabs.harvard.edu/abs/2019A%26A...624A..20M/abstract

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    tag : str
        Tag name in the database.
    file_name : str
        Filename with the isochrones data.

    Returns
    -------
    NoneType
        None
    """

    # M      age     S_0             L          S(t)            R        Teff
    # (M_J)  (Gyr)   (k_B/baryon)    (L_sol)    (k_B/baryon)    (R_J)    (K)
    mass, age, _, luminosity, _, radius, teff = np.loadtxt(file_name, unpack=True)

    age *= 1e3  # (Myr)
    luminosity = np.log10(luminosity)

    mass_cgs = 1e3 * mass * constants.M_JUP  # (g)
    radius_cgs = 1e2 * radius * constants.R_JUP  # (cm)

    logg = np.log10(1e3 * constants.GRAVITY * mass_cgs / radius_cgs**2)

    print(f"Adding isochrones: {tag}...", end="", flush=True)

    isochrones = np.vstack((age, mass, teff, luminosity, logg))
    isochrones = np.transpose(isochrones)

    index_sort = np.argsort(isochrones[:, 0])
    isochrones = isochrones[index_sort, :]

    dset = database.create_dataset(f"isochrones/{tag}/evolution", data=isochrones)

    dset.attrs["model"] = "marleau"

    print(" [DONE]")


def add_sonora(database, input_path):
    """
    Function for adding the
    `Sonora Bobcat <https://zenodo.org/record/5063476>`_
    isochrone data to the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    input_path : str
        Folder where the data is located.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    url = "https://zenodo.org/record/5063476/files/evolution_and_photometery.tar.gz"

    input_file = "evolution_and_photometery.tar.gz"
    data_file = os.path.join(input_path, input_file)
    sub_folder = input_file.split(".", maxsplit=1)[0]
    data_folder = os.path.join(input_path, sub_folder)

    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    if not os.path.isfile(data_file):
        print("Downloading Sonora Bobcat evolution (929 kB)...", end="", flush=True)
        urllib.request.urlretrieve(url, data_file)
        print(" [DONE]")

    print("Unpacking Sonora Bobcat evolution (929 kB)", end="", flush=True)
    with tarfile.open(data_file) as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, data_folder)
    print(" [DONE]")

    iso_files = [
        "evo_tables+0.0/nc+0.0_co1.0_age",
        "evo_tables+0.5/nc+0.5_co1.0_age",
        "evo_tables-0.5/nc-0.5_co1.0_age",
    ]

    labels = ["[M/H] = +0.0", "[M/H] = +0.5", "[M/H] = -0.5"]

    for i, item in enumerate(iso_files):
        iso_file = f"evolution_tables/{item}"
        iso_path = os.path.join(data_folder, iso_file)

        isochrones = []

        with open(iso_path, encoding="utf-8") as open_file:
            for j, line in enumerate(open_file):
                if j == 0 or " " not in line.strip():
                    continue

                # age(Gyr)  M/Msun  log(L/Lsun)  Teff(K)  log(g)  R/Rsun
                param = list(filter(None, line.strip().split(" ")))
                param = list(map(float, param))

                param[0] = 1e3 * param[0]  # (Gyr) -> (Myr)
                param[1] = (
                    param[1] * constants.M_SUN / constants.M_JUP
                )  # (Msun) -> (Mjup)

                isochrones.append([param[0], param[1], param[3], param[2], param[4]])

            print(f"Adding isochrones: Sonora {labels[i]}...", end="", flush=True)

            metal = labels[i].split(" ")[2]

            dset = database.create_dataset(
                f"isochrones/sonora{metal}/evolution", data=isochrones
            )

            dset.attrs["model"] = "sonora"

            print(" [DONE]")
            print(f"Database tag: sonora{metal}")


def add_ames(database, input_path):
    """
    Function for adding the AMES-Cond and AMES-Dusty
    isochrone data to the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    input_path : str
        Folder where the data is located.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    url_list = [
        "https://home.strw.leidenuniv.nl/~stolker/species/"
        "model.AMES-Cond-2000.M-0.0.MKO.Vega",
        "https://home.strw.leidenuniv.nl/~stolker/species/"
        "model.AMES-dusty.M-0.0.MKO.Vega",
    ]

    iso_tags = ["AMES-Cond", "AMES-Dusty"]
    iso_size = ["235 kB", "182 kB"]

    for i, url_item in enumerate(url_list):
        input_file = url_item.split("/")[-1]
        data_file = os.path.join(input_path, input_file)

        if not os.path.isfile(data_file):
            print(
                f"Downloading {iso_tags[i]} isochrones ({iso_size[i]})...",
                end="",
                flush=True,
            )
            urllib.request.urlretrieve(url_item, data_file)
            print(" [DONE]")

        add_manual(database=database, tag=iso_tags[i].lower(), file_name=data_file)


def add_btsettl(database, input_path):
    """
    Function for adding the BT-Settl isochrone data to the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    input_path : str
        Folder where the data is located.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    url_iso = (
        "https://home.strw.leidenuniv.nl/~stolker/species/"
        "model.BT-Settl.M-0.0.MKO.Vega"
    )

    iso_tag = "BT-Settl"
    iso_size = "113 kB"

    input_file = url_iso.rsplit("/", maxsplit=1)[-1]
    data_file = os.path.join(input_path, input_file)

    if not os.path.isfile(data_file):
        print(f"Downloading {iso_tag} isochrones ({iso_size})...", end="", flush=True)
        urllib.request.urlretrieve(url_iso, data_file)
        print(" [DONE]")

    add_manual(database=database, tag=iso_tag.lower(), file_name=data_file)


def add_nextgen(database, input_path):
    """
    Function for adding the NextGen isochrone data to the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    input_path : str
        Folder where the data is located.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    url_iso = (
        "https://home.strw.leidenuniv.nl/~stolker/species/"
        "model.NextGen.M-0.0.MKO.Vega"
    )

    iso_tag = "NextGen"
    iso_size = "177 kB"

    input_file = url_iso.rsplit("/", maxsplit=1)[-1]
    data_file = os.path.join(input_path, input_file)

    if not os.path.isfile(data_file):
        print(f"Downloading {iso_tag} isochrones ({iso_size})...", end="", flush=True)
        urllib.request.urlretrieve(url_iso, data_file)
        print(" [DONE]")

    add_manual(database=database, tag=iso_tag.lower(), file_name=data_file)


def add_saumon(database, input_path):
    """
    Function for adding the Saumon & Marley (2008)
    isochrone data to the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    input_path : str
        Folder where the data is located.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    url_iso = "https://home.strw.leidenuniv.nl/~stolker/species/BD_evolution.tgz"

    iso_tag = "Saumon & Marley (2008)"
    iso_size = "800 kB"

    data_folder = os.path.join(input_path, "saumon_marley_2008")

    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    input_file = url_iso.rsplit("/", maxsplit=1)[-1]
    data_file = os.path.join(input_path, input_file)

    if not os.path.isfile(data_file):
        print(f"Downloading {iso_tag} isochrones ({iso_size})...", end="", flush=True)
        urllib.request.urlretrieve(url_iso, data_file)
        print(" [DONE]")

    print(f"Unpacking {iso_tag} isochrones ({iso_size})", end="", flush=True)
    with tarfile.open(data_file) as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, data_folder)
    print(" [DONE]")

    iso_files = [
        "nc_solar_age",
        "nc-0.3_age",
        "nc+0.3_age",
        "f2_solar_age",
        "hybrid_solar_age",
    ]

    labels = [
        "Cloudless [M/H] = 0.0",
        "Cloudless [M/H] = -0.3",
        "Cloudless [M/H] = +0.3",
        "Cloudy f_sed = 2",
        "Hybrid (cloudless / f_sed = 2)",
    ]

    db_tags = [
        "saumon2008-nc_solar",
        "saumon2008-nc_-0.3",
        "saumon2008-nc_+0.3",
        "saumon2008-f2_solar",
        "saumon2008-hybrid_solar",
    ]

    for j, item in enumerate(iso_files):
        iso_path = os.path.join(data_folder, item)

        isochrones = []

        with open(iso_path, encoding="utf-8") as open_file:
            for i, line in enumerate(open_file):
                if i == 0 or " " not in line.strip():
                    continue

                # age(Gyr)  M/Msun  log(L/Lsun)  Teff(K)  log(g)  R/Rsun
                param = list(filter(None, line.strip().split(" ")))
                param = list(map(float, param))

                param[0] = 1e3 * param[0]  # (Gyr) -> (Myr)
                param[1] = (
                    param[1] * constants.M_SUN / constants.M_JUP
                )  # (Msun) -> (Mjup)

                isochrones.append([param[0], param[1], param[3], param[2], param[4]])

        print(f"Adding isochrones: {iso_tag} {labels[j]}...", end="", flush=True)

        dset = database.create_dataset(
            f"isochrones/{db_tags[j]}/evolution", data=isochrones
        )

        dset.attrs["model"] = "saumon2008"

        print(" [DONE]")
        print(f"Database tag: {db_tags[j]}")


def add_baraffe2015(database, input_path):
    """
    Function for adding the Baraffe et al. (2015)
    isochrone data to the database.

    Parameters
    ----------
    database : h5py._hl.files.File
        Database.
    input_path : str
        Folder where the data is located.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    url_iso = (
        "http://perso.ens-lyon.fr/isabelle.baraffe/BHAC15dir/BHAC15_tracks+structure"
    )

    iso_tag = "Baraffe et al. (2015)"
    iso_size = "1.4 MB"
    db_tag = "baraffe2015"

    input_file = url_iso.rsplit("/", maxsplit=1)[-1]
    data_file = os.path.join(input_path, input_file)

    if not os.path.isfile(data_file):
        print(f"Downloading {iso_tag} isochrones ({iso_size})...", end="", flush=True)
        urllib.request.urlretrieve(url_iso, data_file)
        print(" [DONE]")

    # M/Ms, log t(yr), Teff, log(L/Ls), log(g), R/Rs,
    # Log(Li/Li0), log(Tc), log(ROc), Mrad, Rrad, k2conv, k2rad
    mass, log_age, teff, log_lum, log_g, _, _, _, _, _, _, _, _ = np.loadtxt(
        data_file, unpack=True, skiprows=45, comments="!"
    )

    age = 1e-6 * 10.0**log_age  # (Myr)
    mass *= constants.M_SUN / constants.M_JUP  # (Msun) -> (Mjup)

    isochrones = np.column_stack([age, mass, teff, log_lum, log_g])

    print(f"Adding isochrones: {iso_tag}...", end="", flush=True)

    dset = database.create_dataset(f"isochrones/{db_tag}/evolution", data=isochrones)

    dset.attrs["model"] = "baraffe2015"

    print(" [DONE]")

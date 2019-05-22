# Copyright (C) 2019 Simon Biggs and Cancer Care Associates

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version (the "AGPL-3.0+").

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License and the additional terms for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# ADDITIONAL TERMS are also included as allowed by Section 7 of the GNU
# Affero General Public License. These additional terms are Sections 1, 5,
# 6, 7, 8, and 9 from the Apache License, Version 2.0 (the "Apache-2.0")
# where all references to the definition "License" are instead defined to
# mean the AGPL-3.0+.

# You should have received a copy of the Apache-2.0 along with this
# program. If not, see <http://www.apache.org/licenses/LICENSE-2.0>.


import os

import pytest

import numpy as np
import matplotlib.pyplot as plt

import pydicom

from pymedphys.deliverydata import (
    # Import using the same API as the webapp
    dicom_to_delivery_data, delivery_data_to_dicom
)

from pymedphys_core.deliverydata.dicom import (
    get_gantry_angles_from_dicom, get_all_masked_delivery_data,
    maintain_order_unique,
    filter_out_irrelevant_control_points,
    get_metersets_from_delivery_data, get_gantry_angle_masks)

from pymedphys_fileformats.trf import delivery_data_from_logfile

from pymedphys_core.mudensity import mu_density_from_delivery_data

# pylint: disable=redefined-outer-name

DATA_DIRECTORY = os.path.join(
    os.path.dirname(__file__), "data", "multi_fraction_groups")
DICOM_FILEPATH = os.path.abspath(os.path.join(
    DATA_DIRECTORY, "RP.2.16.840.1.114337.1.1.1558497888.0_Anonymised.dcm"))
LOGFILE_FILEPATH = os.path.abspath(os.path.join(
    DATA_DIRECTORY, "imrt.trf"))


@pytest.fixture
def loaded_dicom_dataset():
    return pydicom.dcmread(DICOM_FILEPATH, force=True)


@pytest.fixture
def logfile_delivery_data():
    return delivery_data_from_logfile(LOGFILE_FILEPATH)


@pytest.fixture
def loaded_dicom_gantry_angles(loaded_dicom_dataset):
    return get_gantry_angles_from_dicom(loaded_dicom_dataset)


@pytest.fixture
def filtered_logfile_delivery_data(logfile_delivery_data):
    return filter_out_irrelevant_control_points(logfile_delivery_data)


def test_get_metersets_from_delivery_data(filtered_logfile_delivery_data,
                                          loaded_dicom_gantry_angles):
    expected = [189.5728, 57.0711, 190.006]
    gantry_tol = 3
    all_masked_delivery_data = get_all_masked_delivery_data(
        filtered_logfile_delivery_data, loaded_dicom_gantry_angles, gantry_tol)

    metersets = get_metersets_from_delivery_data(all_masked_delivery_data)

    assert expected == metersets


def test_mudensity_agreement(loaded_dicom_dataset, logfile_delivery_data):
    dicom_delivery_data = dicom_to_delivery_data(loaded_dicom_dataset)

    dicom_mu_density = mu_density_from_delivery_data(
        dicom_delivery_data, grid_resolution=5)
    logfile_mu_density = mu_density_from_delivery_data(
        logfile_delivery_data, grid_resolution=5)

    diff = logfile_mu_density - dicom_mu_density
    max_diff = np.max(np.abs(diff))
    std_diff = np.std(diff)
    try:
        assert max_diff < 4.1
        assert std_diff < 0.4
    except AssertionError:
        max_val = np.max([
            np.max(logfile_mu_density),
            np.max(dicom_mu_density)
        ])

        plt.figure()
        plt.pcolormesh(dicom_mu_density, vmin=0, vmax=max_val)
        plt.colorbar()

        plt.figure()
        plt.pcolormesh(logfile_mu_density, vmin=0, vmax=max_val)
        plt.colorbar()

        plt.figure()
        plt.pcolormesh(
            logfile_mu_density - dicom_mu_density,
            vmin=-max_diff, vmax=max_diff, cmap='bwr')
        plt.colorbar()
        plt.show()
        raise


def test_round_trip_dd2dcm2dd(loaded_dicom_dataset,
                              filtered_logfile_delivery_data):
    original = filtered_logfile_delivery_data
    template = loaded_dicom_dataset

    dicom = delivery_data_to_dicom(original, template)
    processed = dicom_to_delivery_data(dicom)

    assert np.all(
        np.around(original.monitor_units, 2) ==
        np.around(processed.monitor_units, 2))

    assert np.all(
        np.around(original.gantry, 2) ==
        np.around(processed.gantry, 2))

    assert np.all(
        np.around(original.mlc, 2) ==
        np.around(processed.mlc, 2))

    assert np.all(
        np.around(original.jaw, 2) ==
        np.around(processed.jaw, 2))

    # Collimator not currently handled appropriately
    assert np.all(
        np.around(original.collimator, 2) ==
        np.around(processed.collimator, 2))


def test_round_trip_dcm2dd2dcm(loaded_dicom_dataset,
                               loaded_dicom_gantry_angles):
    original = loaded_dicom_dataset
    original_gantry_angles = loaded_dicom_gantry_angles

    delivery_data = dicom_to_delivery_data(original)
    processed = delivery_data_to_dicom(
        delivery_data, original)

    assert (
        num_of_control_points(original) == num_of_control_points(processed)
    )

    assert (
        maintain_order_unique(delivery_data.gantry) == original_gantry_angles)

    processed_gantry_angles = get_gantry_angles_from_dicom(processed)

    assert original_gantry_angles == processed_gantry_angles

    assert (
        source_to_surface_distances(original) ==
        source_to_surface_distances(processed))

    assert first_mlc_positions(original) == first_mlc_positions(processed)

    assert str(original) == str(processed)


def num_of_control_points(dicom_dataset):
    return [
        len(beam.ControlPointSequence)
        for beam in dicom_dataset.BeamSequence
    ]


def source_to_surface_distances(dicom_dataset):
    SSDs = [
        {
            control_point.SourceToSurfaceDistance
            for control_point in beam_sequence.ControlPointSequence
        }
        for beam_sequence in dicom_dataset.BeamSequence
    ]

    return SSDs


def first_mlc_positions(dicom_dataset):
    result = [
        beam_sequence.ControlPointSequence[0].BeamLimitingDevicePositionSequence[1].LeafJawPositions
        for beam_sequence in dicom_dataset.BeamSequence
    ]

    return result

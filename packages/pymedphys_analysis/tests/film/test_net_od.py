# Copyright (C) 2019 Simon Biggs

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
"""Notes

Make the prescan be the moving image, that way the treatment field is
not interpolated during the netOD calc and is left in the same coords as
the laser marked image.

"""

import os
import json

import numpy as np

from pymedphys_analysis.film import calc_net_od
from pymedphys_analysis.film.fixtures import BASELINES_DIR, prescans, postscans  # pylint: disable=unused-import

CREATE_BASELINE = True
BASELINE_FILEPATH = os.path.join(BASELINES_DIR, 'net_od.json')


def test_net_od(prescans, postscans):  # pylint: disable=redefined-outer-name
    keys = prescans.keys()
    assert keys == postscans.keys()

    if not CREATE_BASELINE:
        with open(BASELINE_FILEPATH, 'r') as a_file:
            baselines = json.load(a_file)
    else:
        baselines = {str(key): None for key in keys}

    results = {}

    keys_to_use = [200, 600]

    for key in keys_to_use:
        results[key] = np.around(calc_net_od(prescans[key], postscans[key]),
                                 decimals=4).tolist()

    if CREATE_BASELINE:
        with open(BASELINE_FILEPATH, 'w') as a_file:
            json.dump(results, a_file)

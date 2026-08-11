# backend/app/services/hsds.py

import os
from typing import Any
import h5pyd
from app.models.exceptions import (
    DomainNotFoundError,
    GroupNotFoundError,
    DatasetNotFoundError,
    AttributeNotFoundError,
)

HSDS_URL = os.getenv("HSDS_URL", "http://hsds:5101")


class HSDSClient:

    def __init__(self):
        self.endpoint = HSDS_URL
        self.username = os.getenv("HSDS_USERNAME")
        self.password = os.getenv("HSDS_PASSWORD")

    def _serialize_attrs(self, attrs):
        result = {}

        for key, value in attrs.items():
            if hasattr(value, "tolist"):
                result[key] = value.tolist()
            else:
                result[key] = value

        return result

    def _is_scalar(self, dataset: h5pyd.Dataset) -> bool:
        return dataset.shape == () or dataset.shape == (1,)

    def _is_vector(self, dataset: h5pyd.Dataset) -> bool:
        return len(dataset.shape) == 1 and dataset.shape[0] > 1

    def _is_matrix(self, dataset: h5pyd.Dataset) -> bool:
        return len(dataset.shape) == 2 and dataset.shape[0] > 1 and dataset.shape[1] > 1

    def _is_higher_dimensional(self, dataset: h5pyd.Dataset) -> bool:
        return len(dataset.shape) > 2 and all(dim > 1 for dim in dataset.shape)

    def _open_raw(self, domain: str, mode: str = "r"):
        return h5pyd.File(
            domain,
            mode,
            endpoint=self.endpoint,
            username=self.username,
            password=self.password,
        )

    def _open(self, domain: str, mode: str = "r"):
        if not self.domain_exists(domain):
            raise DomainNotFoundError(f"Domain '{domain}' not found")
        return self._open_raw(domain, mode)

    def get_domain(self, domain: str):
        with self._open(domain) as f:
            return {
                "domain": domain,
                "root": f["/"].id.id,
                "attrs": self._serialize_attrs(f.attrs),
            }

    def domain_exists(self, domain: str) -> bool:
        try:
            with self._open_raw(domain):
                return True
        except Exception:
            return False

    def is_group(self, domain: str, path: str) -> bool:
        try:
            with self._open(domain) as f:
                obj = f[path]
                return isinstance(obj, h5pyd.Group)
        except DomainNotFoundError:
            return False
        except KeyError:
            return False

    def is_dataset(self, domain: str, path: str) -> bool:
        try:
            with self._open(domain) as f:
                obj = f[path]
                return isinstance(obj, h5pyd.Dataset)
        except DomainNotFoundError:
            return False
        except KeyError:
            return False

    def get_group(self, domain: str, path: str = "/"):
        if not self.is_group(domain, path):
            raise GroupNotFoundError(f"Group '{path}' not found in domain '{domain}'")
        with self._open(domain) as f:
            group = f[path]
            return {
                "name": group.name,
                "attrs": self._serialize_attrs(group.attrs),
                "members": list(group.keys()),
            }

    def list_group_members(self, domain: str, path: str = "/"):
        if not self.is_group(domain, path):
            raise GroupNotFoundError(f"No groups found in {path} of domain '{domain}'")
        with self._open(domain) as f:
            return list(f[path].keys())

    def get_dataset_by_path(self, domain: str, path: str):
        if not self.is_dataset(domain, path):
            raise DatasetNotFoundError(
                f"Dataset '{path}' not found in domain '{domain}'"
            )

        with self._open(domain) as f:
            ds = f[path]
            return {
                "name": ds.name,
                "shape": ds.shape,
                "dtype": str(ds.dtype),
                "attrs": self._serialize_attrs(ds.attrs),
            }

    def _get_vector_bytes(self, dataset: h5pyd.Dataset, slice_start: int = None, slice_end: int = None) -> bytes:
        if not self._is_vector(dataset):
            raise ValueError("Dataset is not a vector")
        if slice_start is None:
            slice_start = 0
        if slice_end is None:
            slice_end = dataset.shape[0]
        return dataset[slice_start:slice_end].tobytes()

    def _get_matrix_bytes(self, dataset: h5pyd.Dataset, slice_start: int = None, slice_end: int = None) -> bytes:
        if not self._is_matrix(dataset):
            raise ValueError("Dataset is not a matrix")
        if slice_start is None:
            slice_start = 0
        if slice_end is None:
            slice_end = dataset.shape[0]
        return dataset[slice_start:slice_end, :].tobytes()

    def _get_scalar(self, dataset: h5pyd.Dataset) -> Any:
        if not self._is_scalar(dataset):
            raise ValueError("Dataset is not a scalar")
        return dataset[()].item()

    def get_dataset_values_by_path(
        self,
        domain: str,
        path: str,
        slice_start: int = None,
        slice_end: int = None,
    ):
        if not self.is_dataset(domain, path):
            raise DatasetNotFoundError(
                f"Dataset '{path}' not found in domain '{domain}'"
            )
        with self._open(domain) as f:
            obj = f[path]
            if self._is_scalar(obj):
                return {"value": self._get_scalar(obj)}
            elif self._is_vector(obj):
                return self._get_vector_bytes(obj, slice_start, slice_end)
            elif self._is_matrix(obj):
                return self._get_matrix_bytes(obj, slice_start, slice_end)
            else:
                raise ValueError("Dataset is not a scalar, vector, or matrix")

    def get_attributes(
        self,
        domain: str,
        path: str,
    ):
        if not self.is_group(domain, path) and not self.is_dataset(domain, path):
            raise AttributeNotFoundError(
                f"Attributes not found for '{path}' in domain '{domain}'"
            )
        with self._open(domain) as f:
            obj = f[path]
            return self._serialize_attrs(obj.attrs)

    def visit(self, domain: str):
        paths = []
        with self._open(domain) as f:

            def visitor(name):
                paths.append(name)

            f.visit(visitor)
        return paths

    def health(self):
        try:
            with self._open("/"):
                pass
            return {"status": "ok"}
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }

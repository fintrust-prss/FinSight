"""
AWS adapter package — Stage 2 implementations.

All classes in this package raise ``NotImplementedError`` with a clear
message pointing to the Stage 2 migration task.

To implement Stage 2:
  1. ``pip install boto3 aioboto3``
  2. Implement each class below conforming to the base interface.
  3. Set ``CLOUD_PROVIDER=aws`` in your environment.
  4. Zero changes to service/route code required.
"""

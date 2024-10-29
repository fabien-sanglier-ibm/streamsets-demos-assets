Simple Minio commands
=========================

Ref: https://min.io/docs/minio/linux/reference/minio-mc.html

```zsh
mc alias set myminio https://localhost:55280 ACCESSKEY ACCESSSECRET --insecure
```

Upload content to bucket:

```zsh
mc cp --insecure --recursive ~/streamsets-libs-extras/* myminio/streamsets-datacollector-libs-collection1/streamsets-libs-extras/
```

Potentially upload other lib in the user-libs:

```zsh
mc cp --insecure --recursive ~/streamsets-user-libs/* myminio/streamsets-datacollector-libs-collection1/user-libs/
```

List what's in the bucket:
```zsh
mc ls --insecure myminio/streamsets-datacollector-libs-collection1/
```
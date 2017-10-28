import hashlib
import logging
import os
import re

from guild import cli
from guild import modelfile
from guild import pip_util
from guild import util
from guild import var

RESOURCE_TERM = r"[a-zA-Z0-9_\-\.]+"

class DependencyError(Exception):
    pass

class ResolutionContext(object):

    def __init__(self, target_dir, opdef):
        self.target_dir = target_dir
        self.opdef = opdef

class Resource(object):

    def __init__(self, resdef, ctx):
        self.resdef = resdef
        self.ctx = ctx

    def _link_to_source(self, source_path):
        link = self._link_path(source_path)
        util.ensure_dir(os.path.dirname(link))
        logging.debug("resolving source '%s' as link '%s'", source_path, link)
        os.symlink(source_path, link)

    def _link_path(self, source_path):
        basename = os.path.basename(source_path)
        res_path = self.resdef.path or ""
        if os.path.isabs(res_path):
            raise DependencyError(
                "invalid path '%s' in resource '%s' (path must be relative)"
                % (res_path, self.resdef.name))
        return os.path.join(self.ctx.target_dir, res_path, basename)

    def resolve(self):
        cli.out("Resolving %s requirement" % self.resdef.name)
        for source in self.resdef.sources:
            if isinstance(source, modelfile.FileSource):
                self._resolve_file_source(source)
            elif isinstance(source, modelfile.URLSource):
                self._resolve_url_source(source)
            else:
                raise AssertionError(source)

    def _resolve_file_source(self, source):
        assert isinstance(source, modelfile.FileSource), source
        working_dir = os.path.dirname(self.resdef.modelfile.src)
        source_path = os.path.join(working_dir, source.path)
        _verify_file(source_path, source.sha256, self.ctx)
        self._link_to_source(source_path)

    def _resolve_url_source(self, source):
        assert isinstance(source, modelfile.URLSource), source
        source_path = _ensure_url_source(source)
        self._link_to_source(source_path)

def _verify_file(path, sha256, ctx):
    _verify_file_exists(path, ctx)
    if sha256:
        _verify_file_hash(path, sha256)

def _verify_file_exists(path, ctx):
    if not os.path.exists(path):
        raise DependencyError(
            "'%s' required by operation '%s' does not exist"
            % (path, ctx.opdef.fullname))

def _verify_file_hash(path, sha256):
    actual = util.file_sha256(path)
    if actual != sha256:
        raise DependencyError(
            "unexpected sha256 for '%s' (expected %s but got %s)"
            % (path, sha256, actual))

def _ensure_url_source(source):
    download_dir = _download_dir_for_url(source.parsed_url)
    util.ensure_dir(download_dir)
    try:
        return pip_util.download_url(source.url, download_dir, source.sha256)
    except pip_util.HashMismatch as e:
        raise DependencyError(
            "bad sha256 for '%s' (expected %s but got %s)"
            % (source.url, e.expected, e.actual))

def _download_dir_for_url(parsed_url):
    key = "\n".join(parsed_url).encode("utf-8")
    digest = hashlib.sha224(key).hexdigest()
    return os.path.join(var.cache_dir("resources"), digest)

def _dep_desc(dep):
    return "%s:%s" % (dep.opdef.modeldef.name, dep.opdef.name)

def resolve(dependencies, ctx):
    for dep in dependencies:
        resource = _dependency_resource(dep.spec, ctx)
        resource.resolve()

def _dependency_resource(spec, ctx):
    res = util.find_apply(
        [_model_resource,
         _modelfile_resource,
         _packaged_resource],
        spec, ctx)
    if res:
        return res
    raise DependencyError(
        "invalid dependency '%s' in operation '%s'"
        % (spec, ctx.opdef.fullname))

def _model_resource(spec, ctx):
    m = re.match(r"(%s)$" % RESOURCE_TERM, spec)
    if m is None:
        return None
    res_name = m.group(1)
    return _modeldef_resource(ctx.opdef.modeldef, res_name, ctx)

def _modeldef_resource(modeldef, res_name, ctx):
    resdef = modeldef.get_resource(res_name)
    if resdef is None:
        raise DependencyError(
            "resource '%s' required by operation '%s' is not defined"
            % (res_name, ctx.opdef.fullname))
    return Resource(resdef, ctx)

def _modelfile_resource(spec, ctx):
    m = re.match(r"(%s):(%s)$" % (RESOURCE_TERM, RESOURCE_TERM), spec)
    if m is None:
        return None
    model_name = m.group(1)
    modeldef = ctx.opdef.modelfile.get(model_name)
    if modeldef is None:
        raise DependencyError(
            "model in resource '%s' required by operation "
            "'%s' is not defined"
            % (spec, ctx.opdef.fullname))
    res_name = m.group(2)
    return _modeldef_resource(modeldef, res_name, ctx)

def _packaged_resource(_spec, _ctx):
    # TODO
    return None

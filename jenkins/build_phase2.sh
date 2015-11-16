umask 022

# Select mock config for the kernel we are building with
REPO=${JP_REPO:-sspl}
PROJECT=${JP_NEO_RELEASE:-osaint}
MOCK_CONFIG=mock_${PROJECT}
SCM_URL=${JP_SCM_URL:-http://seagate.com}
VERSION=${JP_VERSION:-1.0}
NEO_ID=${JP_NEO_ID:-o.1.0}
SOURCE=${REPO}-${VERSION}.tgz
_PWD=$(pwd)
WORKSPACE=${WORKSPACE:-$_PWD}
BUILD_NUMBER=${BUILD_NUMBER:-3}

if [ -x /build/bin/spec_update.sh ] ; then
  SPECUPDATE=/build/bin/spec_update.sh
else
  SPECUPDATE=${WORKSPACE}/jenkins/spec_update.sh
fi

RPMVER=${VERSION}.${NEO_ID}
if [ -d ${WORKSPACE}/.git ] ; then
    SCM_VER=$(git rev-list --max-count=1 HEAD | cut -c1-6)
fi
if [ -d ${WORKSPACE}/.svn ] ; then
    SCM_VER=$(svn info ${repo_dir} 2>/dev/null | grep "Revision:" | cut -f2 -d" ")
fi

if [ -n "${SCM_VER}" ] ; then
   RPMREL=${BUILD_NUMBER}.${SCM_VER}
else
   RPMREL=${BUILD_NUMBER}
fi


# Create output directory
RPMDIR=${WORKSPACE}/RPMBUILD
rm -rf ${RPMDIR}
mkdir -p ${RPMDIR}/SOURCE
mkdir -p ${RPMDIR}/SPECS

# Create tarball.  We will share one for all spec files.
cd ./$(git rev-parse --show-cdup) &&
  git archive --format=tar --prefix=${REPO}/ HEAD . | gzip > RPMBUILD/SOURCE/${SOURCE}

# Initialize chroot.
if [ -z "${NOINIT}" ] ; then
    mock -r ${MOCK_CONFIG} --resultdir ${RPMDIR} --init
fi

rm -rf build_failed

# Create versioned spec file and rebuild package for each spec we find.
ls */*.spec | while read SPECFILE; do
  PACKAGE=$(basename ${SPECFILE})
  PACKAGE=${PACKAGE%%.spec}

  # spec_update expects this name
  ln -s ${SOURCE} RPMBUILD/SOURCE/${PACKAGE}.tgz

  sh -x ${SPECUPDATE} ${PACKAGE} ${RPMVER} ${SCM_URL} ${WORKSPACE} ${RPMDIR} ${RPMREL} ${WORKSPACE}/${SPECFILE}

  mock --buildsrpm -r ${MOCK_CONFIG} --spec ${RPMDIR}/SPECS/${PACKAGE}.spec --sources ${RPMDIR}/SOURCE --resultdir ${RPMDIR} --no-clean --no-cleanup-after
  rval=$?
  if [ "$rval" != "0" ] ; then
      touch build_failed
  fi

  mock --rebuild -r ${MOCK_CONFIG} --no-clean --no-cleanup-after -v --rebuild ${RPMDIR}/${PACKAGE}*.src.rpm --resultdir ${RPMDIR}
  rval=$?
  if [ "$rval" != "0" ] ; then
      touch build_failed
  fi

done

if [ -f build_failed ] ; then
    echo "RPM Build(s) failed"
    exit -3
else
    echo "Complete Build"
    exit 0
fi

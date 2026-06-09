#### NOTE: if building locally you may need to do the following:
####
#### yum install rpmdevtools -y
#### spectool -g -R rpm/quads-client.spec
####
#### At this point you can use rpmbuild -ba quads-client.spec
#### this is because our Source0 is a remote Github location
####
#### Our upstream repository is located here:
#### https://copr.fedorainfracloud.org/coprs/quadsdev/quads-client
####

%define name quads-client
%define reponame quads-client
%define branch main
%define version 0.8.1
%define build_timestamp %{lua: print(os.date("%Y%m%d"))}

Summary: QUADS Client TUI Shell for managing multiple QUADS server instances
Name: %{name}
Version: %{version}
Release: %{build_timestamp}
Source0: https://github.com/sadsfae/quads-client/archive/%{branch}.tar.gz#/%{name}-%{version}-%{release}.tar.gz
License: GPLv3
BuildRoot: %{_tmppath}/%{name}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: QUADS Project
Packager: QUADS Project
BuildRequires: python3-devel >= 3.13
BuildRequires: python3-setuptools
BuildRequires: desktop-file-utils
Requires: python3 >= 3.13
Requires: python3-cmd2 >= 2.0.0
Requires: quads-lib >= 0.1.9
Requires: python3-tabulate >= 0.9.0
Requires: python3-argcomplete >= 3.1.2
Requires: python3-PyYAML >= 6.0.0
Requires: python3-jwt >= 2.8.0
Requires: python3-rich >= 13.0.0
Requires: python3-requests >= 2.31.0
Requires: python3-urllib3 >= 2.0.0
Requires: bash-completion

AutoReq: no

Url: https://quads.dev

%description

QUADS Client is an interactive TUI (Text User Interface) shell for managing
multiple QUADS (QUADS Automated Deployment System) server instances.

Features include:
 * Multi-server connection management with bearer token authentication
 * Interactive cmd2-based shell with command history and tab completion
 * Self-scheduling mode (SSM) for non-admin users
 * Cloud management commands (list, create, delete)
 * Real-time provisioning progress tracking
 * SQLite-based persistent command history
 * Thin wrapper design with server-side authorization

QUADS Client requires Python 3.13 or later and communicates with QUADS
servers via the python-quads-lib API wrapper.

%prep
%autosetup -n %{reponame}-%{branch}

%build
%py3_build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_datadir}/doc/quads-client
%py3_install

# Install example configuration
install -m 0644 conf/quads-client.yml.example %{buildroot}%{_datadir}/doc/quads-client/

# Install GUI desktop file
desktop-file-install --dir=%{buildroot}%{_datadir}/applications desktop/quads-client-gui.desktop

# Install GUI icon
install -Dm 0644 desktop/icons/quads-client.png %{buildroot}%{_datadir}/icons/hicolor/128x128/apps/quads-client.png

%clean
rm -rf %{buildroot}

%package gui
Summary: GUI for QUADS Client
Requires: %{name} = %{version}-%{release}
Requires: python3-tkinter >= 3.13

%description gui
Graphical user interface for QUADS Client using tkinter.
Provides an intuitive GUI for managing QUADS servers, scheduling
hosts, and monitoring assignments. Requires X11/Wayland display.

Theme packages (ttkthemes, sv-ttk) are installed as Python dependencies.
Falls back to built-in 'clam' theme if pip packages unavailable.

%files
%doc README.md
%license LICENSE
%{_bindir}/quads-client
%{python3_sitelib}/quads_client/
%{python3_sitelib}/quads_client-*.egg-info/
%{_datadir}/doc/quads-client/

%files gui
%{_bindir}/quads-client-gui
%{_datadir}/applications/quads-client-gui.desktop
%{_datadir}/icons/hicolor/128x128/apps/quads-client.png

%post
# Enable bash completion globally if available
if [ -x /usr/bin/activate-global-python-argcomplete3 ]; then
    /usr/bin/activate-global-python-argcomplete3 2>/dev/null || true
fi

# First time installation message
if [ "$1" -eq 1 ]; then
echo "======================================================="
echo " QUADS Client installed successfully                   "
echo "======================================================="
echo "                                                       "
echo " To get started:                                       "
echo " Use the interactive add-quads-server command:         "
echo "  quads-client                                         "
echo "  add-quads-server                                     "
echo "  (follow prompts)                                     "
echo "  connect <server_name>                                "
echo "  register your.email@example.com YourPassword123      "
echo "======================================================="
fi
:;

%post gui
# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database %{_datadir}/applications &> /dev/null || :
fi

# Update icon cache
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &> /dev/null || :
fi

if [ "$1" -eq 1 ]; then
echo "======================================================="
echo " QUADS Client GUI installed successfully               "
echo "======================================================="
echo "                                                       "
echo " Launch with: quads-client-gui                         "
echo " Or find it in your Applications menu                  "
echo "                                                       "
echo " Note: Requires X11/Wayland display                    "
echo "======================================================="
fi
:;

%preun
:;

%postun
find %{python3_sitelib}/quads_client 2>/dev/null | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf 2>/dev/null || true
:;

%postun gui
# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database %{_datadir}/applications &> /dev/null || :
fi

# Update icon cache
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &> /dev/null || :
fi
:;

%changelog

* Wed Apr 30 2026 Will Foster <wfoster@redhat.com>
- 1.0.0 initial release
- TUI shell with multi-server support
- Thin wrapper design with server-side authorization
- Self-scheduling mode (SSM) for non-admin users
- Real-time provisioning progress tracking
- SQLite-based persistent command history
- Python 3.13+ requirement
- Removed PyJWT dependency (server handles token validation)
- Black formatted code (line-length 119)
- Comprehensive test suite (44 tests, 61%% coverage)
- Cloud management commands (list, create, delete)
- Connection management (connect, disconnect, status)
- Bearer token authentication via python-quads-lib

from wrf_tools.doctor import dependency_status, environment_report


def test_core_dependencies_are_available():
    statuses = dependency_status()
    assert statuses
    assert all(item.installed for item in statuses if item.required)


def test_environment_report_is_serializable():
    report = environment_report()
    assert report["python"]
    assert report["platform"]
    assert isinstance(report["dependencies"], list)

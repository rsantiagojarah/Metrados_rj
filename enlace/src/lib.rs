use metrado_calculo::{Dimension, DomainError, Partida, Unit};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
fn ask_quantity(name: &str, unit: &str, dimensions: Vec<(String, f64)>) -> PyResult<f64> {
    let unit = Unit::parse(unit).map_err(to_py)?;
    let dimensions = dimensions
        .into_iter()
        .map(|(dimension_name, measure)| Dimension::try_new(&dimension_name, measure))
        .collect::<Result<Vec<_>, _>>()
        .map_err(to_py)?;
    let partida = Partida::try_new(name, unit, dimensions).map_err(to_py)?;
    Ok(partida.quantity().value())
}

fn to_py(error: DomainError) -> PyErr {
    let code = match error {
        DomainError::EmptyName => "empty_name",
        DomainError::EmptyDimensionName => "empty_dimension_name",
        DomainError::NonPositiveMeasure => "non_positive",
        DomainError::DuplicateDimensionName => "duplicate_dimension",
        DomainError::MissingDimension => "missing_dimension",
        DomainError::UnexpectedDimension => "unexpected_dimension",
        DomainError::UnknownUnit => "unknown_unit",
        DomainError::UnknownDiameter => "unknown_diameter",
    };
    PyValueError::new_err(code)
}

#[pyfunction]
fn ask_sheet_steel(
    largo: f64,
    gancho: f64,
    empalme: f64,
    diameter: &str,
    bars: f64,
    elements: f64,
    veces: f64,
) -> PyResult<(f64, f64, f64)> {
    let quantity =
        metrado_calculo::sheet_steel(largo, gancho, empalme, diameter, bars, elements, veces)
            .map_err(to_py)?;
    Ok((quantity.length, quantity.kg_per_m, quantity.weight))
}

#[pyfunction]
#[pyo3(signature = (unit, dimensions, similar, repetitions, direct=None))]
fn ask_sheet_quantity(
    unit: &str,
    dimensions: Vec<(String, f64)>,
    similar: f64,
    repetitions: f64,
    direct: Option<f64>,
) -> PyResult<f64> {
    let dimensions = dimensions
        .into_iter()
        .map(|(name, value)| Dimension::try_new(&name, value))
        .collect::<Result<Vec<_>, _>>()
        .map_err(to_py)?;
    metrado_calculo::sheet_quantity(unit, dimensions, similar, repetitions, direct).map_err(to_py)
}

#[pyfunction]
fn ask_sheet_total(quantities: Vec<f64>) -> PyResult<f64> {
    metrado_calculo::sheet_total(&quantities).map_err(to_py)
}

#[pymodule]
fn _enlace(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(ask_quantity, module)?)?;
    module.add_function(wrap_pyfunction!(ask_sheet_quantity, module)?)?;
    module.add_function(wrap_pyfunction!(ask_sheet_steel, module)?)?;
    module.add_function(wrap_pyfunction!(ask_sheet_total, module)?)?;
    Ok(())
}

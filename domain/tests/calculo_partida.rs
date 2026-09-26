use metrado_calculo::{Dimension, DomainError, Partida, Unit};

#[test]
fn cubic_meter_quantity_is_the_product_of_three_measures() {
    let partida = partida(
        "Muro",
        Unit::CubicMeter,
        &[("largo", 2.0), ("ancho", 3.0), ("alto", 4.0)],
    );
    assert_eq!(partida.quantity().value(), 24.0);
}

#[test]
fn linear_meter_quantity_is_the_length() {
    let partida = partida("Tubo", Unit::LinearMeter, &[("longitud", 5.0)]);
    assert_eq!(partida.quantity().value(), 5.0);
}

#[test]
fn square_meter_quantity_is_length_times_width() {
    let partida = partida("Piso", Unit::SquareMeter, &[("largo", 2.0), ("ancho", 3.0)]);
    assert_eq!(partida.quantity().value(), 6.0);
}

#[test]
fn each_quantity_is_the_count() {
    let partida = partida("Accesorio", Unit::Each, &[("veces", 4.0)]);
    assert_eq!(partida.quantity().value(), 4.0);
}

#[test]
fn dimension_order_does_not_change_quantity() {
    let forward = partida(
        "Muro",
        Unit::CubicMeter,
        &[("largo", 2.0), ("ancho", 3.0), ("alto", 4.0)],
    );
    let reverse = partida(
        "Muro",
        Unit::CubicMeter,
        &[("alto", 4.0), ("ancho", 3.0), ("largo", 2.0)],
    );
    assert_eq!(forward.quantity().value(), reverse.quantity().value());
}

#[test]
fn extra_measure_is_rejected() {
    let error = try_partida(
        "Tubo",
        Unit::LinearMeter,
        &[("longitud", 5.0), ("ancho", 2.0)],
    )
    .unwrap_err();
    assert_eq!(error, DomainError::UnexpectedDimension);
}

#[test]
fn missing_measure_is_rejected() {
    let error = try_partida("Muro", Unit::CubicMeter, &[("largo", 2.0), ("ancho", 3.0)]).unwrap_err();
    assert_eq!(error, DomainError::MissingDimension);
}

#[test]
fn blank_partida_name_is_rejected() {
    let dimension = Dimension::try_new("longitud", 2.0).unwrap();
    let error = Partida::try_new("   ", Unit::LinearMeter, vec![dimension]).unwrap_err();
    assert_eq!(error, DomainError::EmptyName);
}

#[test]
fn duplicate_dimension_name_is_rejected() {
    let first = Dimension::try_new("largo", 2.0).unwrap();
    let second = Dimension::try_new("  largo  ", 3.0).unwrap();
    let error = Partida::try_new("Piso", Unit::SquareMeter, vec![first, second]).unwrap_err();
    assert_eq!(error, DomainError::DuplicateDimensionName);
}

#[test]
fn dimension_rejects_blank_name() {
    let error = Dimension::try_new("   ", 2.0).unwrap_err();
    assert_eq!(error, DomainError::EmptyDimensionName);
}

#[test]
fn dimension_rejects_non_positive_measure() {
    for measure in [0.0, -1.0, f64::NAN, f64::INFINITY] {
        let error = Dimension::try_new("largo", measure).unwrap_err();
        assert_eq!(error, DomainError::NonPositiveMeasure);
    }
}

#[test]
fn unknown_unit_is_rejected() {
    let error = Unit::parse("kg").unwrap_err();
    assert_eq!(error, DomainError::UnknownUnit);
}

fn partida(name: &str, unit: Unit, dimensions: &[(&str, f64)]) -> Partida {
    try_partida(name, unit, dimensions).unwrap()
}

fn try_partida(
    name: &str,
    unit: Unit,
    dimensions: &[(&str, f64)],
) -> Result<Partida, DomainError> {
    let dimensions = dimensions
        .iter()
        .map(|(dimension_name, measure)| Dimension::try_new(dimension_name, *measure))
        .collect::<Result<Vec<_>, _>>()?;
    Partida::try_new(name, unit, dimensions)
}

-- Supply only Quarto's input-file accessor; execute the production filter.
quarto = {
  doc = {
    input_file = function() return os.getenv("GUIDE_TEST_INPUT") end
  }
}
return dofile(os.getenv("GUIDE_TEST_PUBLISHING_FILTER"))
